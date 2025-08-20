import argparse
import json
import logging
import os
import sys
import textwrap
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


try:
    # Preferred SDK import path (subject to SDK version)
    from llama_stack_client import LlamaStackClient  # type: ignore
    from llama_stack_client.lib.agents.agent import Agent, AgentConfig  # type: ignore
except Exception as import_error:  # pragma: no cover - provide actionable error
    raise SystemExit(
        "Failed to import llama-stack-client. Install it with: pip install llama-stack-client"
    ) from import_error


LOGGER = logging.getLogger("deep_search_agent")


@dataclass
class SummarizedBatch:
    query: str
    sources: List[Dict[str, Any]]
    summary_markdown: str
    key_points: List[str]


class LlamaAgentWrapper:
    """Thin wrapper over Llama Stack Agent API to send prompts and get text outputs.

    This wrapper centralizes session lifecycle and provides a simple `chat` method.
    It expects a Llama Stack server running per run.yml (default http://localhost:8321).
    """

    def __init__(
        self,
        base_url: str,
        model_id: str,
        tool_groups: Optional[List[str]] = None,
        system_instructions: Optional[str] = None,
        session_name: Optional[str] = None,
    ) -> None:
        self.client = LlamaStackClient(base_url=base_url)
        # Prefer inlined parameters (Agent will construct a compatible agent_config with "toolgroups")
        self.agent = Agent(
            self.client,
            model=model_id,
            instructions=(
                system_instructions
                or "You are a meticulous research assistant. Be concise and return JSON when requested."
            ),
            tools=tool_groups or [],
            enable_session_persistence=False,
        )
        self.session_id = self._create_session(session_name=session_name)

    def _create_session(self, session_name: Optional[str]) -> str:
        name = session_name or f"deep_search_{int(time.time())}"
        try:
            session_id = self.agent.create_session(session_name=name)
        except AttributeError:
            # Fallback if SDK uses a different name
            session_id = self.agent.start_session(session_name=name)  # type: ignore[attr-defined]
        LOGGER.info("Agent session created: %s", session_id)
        return session_id

    def chat(self, prompt: str, temperature: float = 0.2, max_output_tokens: int = 1200) -> str:
        """Send a user prompt to the agent and return assistant text content.

        The underlying SDK shape can vary. We handle a few likely return shapes.
        """
        messages = [{"role": "user", "content": prompt}]
        # Non-streaming turn for simplicity; Agent returns a Turn object
        turn = self.agent.create_turn(
            messages=messages,
            session_id=self.session_id,
            stream=False,
        )

        # Extract assistant text content from Turn
        text: Optional[str] = None
        try:
            output_msg = getattr(turn, "output_message", None)
            if output_msg is not None:
                text = getattr(output_msg, "content", None) or getattr(output_msg, "text", None)
        except Exception:
            text = None

        if not text:
            # Fallback: stringify
            text = str(turn)

        LOGGER.debug("Agent output (truncated): %s", textwrap.shorten(text, width=300, placeholder="…"))
        return text


class DeepSearchAgent:
    """Deep search agent orchestrating web search via Llama Stack tool runtime and LLM summarization."""

    def __init__(
        self,
        llama_base_url: str,
        model_id: str,
        max_extra_rounds: int = 2,
    ) -> None:
        self.agent = LlamaAgentWrapper(
            base_url=llama_base_url,
            model_id=model_id,
            tool_groups=["builtin::websearch"],
            session_name="deep_search_session",
            system_instructions=(
                "You are a research planner and summarizer. When asked to output JSON, return only valid JSON."
            ),
        )
        self.max_extra_rounds = max_extra_rounds

    def generate_diverse_queries(self, user_question: str) -> List[str]:
        """Use the LLM to propose exactly three diverse web search queries.

        Falls back to a naive heuristic if parsing fails.
        """
        prompt = textwrap.dedent(
            f"""
            You will generate exactly three diverse Google search queries that would help answer the user's question.
            Return ONLY a compact JSON array of strings like ["query1", "query2", "query3"]. Do not add any other text.

            User question: "{user_question}"
            """
        ).strip()
        LOGGER.info("Generating diverse queries…")
        raw = self.agent.chat(prompt, temperature=0.3, max_output_tokens=300)
        try:
            queries = json.loads(raw)
            if not (isinstance(queries, list) and len(queries) == 3 and all(isinstance(q, str) for q in queries)):
                raise ValueError("Expected exactly three string queries")
            LOGGER.info("Queries: %s", queries)
            return queries
        except Exception as parse_error:
            LOGGER.warning("Failed to parse LLM queries as JSON (%s). Falling back to heuristic.", parse_error)
            return [
                user_question,
                f"{user_question} site:wikipedia.org overview",
                f"{user_question} latest developments 2024 2025",
            ]

    def tavily_search(self, query: str, max_results: int = 6) -> List[Dict[str, Any]]:
        """Execute web search and map Tavily results into [{title,url,content}]."""
        LOGGER.info("Searching (web tool): %s", query)
        client = self.agent.client

        # Use the configured builtin websearch tool; fall back requires no discovery
        tool_identifier = "builtin::websearch/web_search"
        try:
            tools = client.tools.list(toolgroup_id="builtin::websearch")
            for t in tools:
                ident = getattr(t, "identifier", None)
                if ident:
                    tool_identifier = ident
                    break
        except Exception:
            pass

        tool_kwargs = {"query": query, "max_results": max_results, "search_depth": "advanced"}
        resp: Any = client.tool_runtime.invoke_tool(tool_name=tool_identifier, kwargs=tool_kwargs)

        # Extract the content payload – Tavily often returns a list of {url,title,text}
        content: Any
        if isinstance(resp, dict):
            content = (
                resp.get("content")
                or resp.get("output")
                or resp.get("results")
                or resp.get("data")
                or resp
            )
        else:
            content = (
                getattr(resp, "content", None)
                or getattr(resp, "output", None)
                or getattr(resp, "results", None)
                or getattr(resp, "data", None)
                or resp
            )

        def looks_like_result(d: Dict[str, Any]) -> bool:
            return any(k in d for k in ("url", "title", "text", "content", "snippet", "description"))

        def gather_from_container(obj: Any) -> List[Any]:
            results: List[Any] = []
            if isinstance(obj, dict):
                # Direct containers of results
                for key in ("results", "data", "items", "hits", "top_k", "json"):
                    val = obj.get(key)
                    if isinstance(val, list):
                        for el in val:
                            results.extend(gather_from_container(el))
                    elif isinstance(val, dict):
                        results.extend(gather_from_container(val))
                # Nested common wrappers
                for key in ("content", "output", "message", "messages"):
                    val = obj.get(key)
                    if isinstance(val, (list, dict)):
                        results.extend(gather_from_container(val))
                # Dicts that embed JSON in a text field (but avoid real result dicts)
                if (
                    isinstance(obj.get("text"), str)
                    and not any(k in obj for k in ("url", "title", "snippet", "description"))
                ):
                    try:
                        parsed_text = json.loads(obj.get("text", ""))
                        results.extend(gather_from_container(parsed_text))
                    except Exception:
                        pass
                # Leaf-like result
                if looks_like_result(obj):
                    results.append(obj)
            elif isinstance(obj, list):
                for el in obj:
                    if isinstance(el, (dict, list)):
                        results.extend(gather_from_container(el))
                    elif isinstance(el, str):
                        # Attempt to parse inline JSON
                        try:
                            parsed = json.loads(el)
                            results.extend(gather_from_container(parsed))
                        except Exception:
                            continue
                    else:
                        # Objects with a text attribute carrying JSON or plain text
                        text_attr = getattr(el, "text", None)
                        json_attr = getattr(el, "json", None)
                        if isinstance(json_attr, (dict, list)):
                            results.extend(gather_from_container(json_attr))
                        elif isinstance(text_attr, str):
                            try:
                                parsed = json.loads(text_attr)
                                results.extend(gather_from_container(parsed))
                            except Exception:
                                pass
            else:
                # Object-like: try common attributes
                try:
                    json_attr = getattr(obj, "json", None)
                    if isinstance(json_attr, (dict, list)):
                        results.extend(gather_from_container(json_attr))
                    for key in ("results", "data", "items", "hits", "top_k"):
                        val = getattr(obj, key, None)
                        if isinstance(val, (dict, list)):
                            results.extend(gather_from_container(val))
                    for key in ("content", "output"):
                        val = getattr(obj, key, None)
                        if isinstance(val, (dict, list)):
                            results.extend(gather_from_container(val))
                    # As a last resort, parse text as JSON
                    text_attr = getattr(obj, "text", None)
                    if isinstance(text_attr, str):
                        try:
                            parsed = json.loads(text_attr)
                            results.extend(gather_from_container(parsed))
                        except Exception:
                            pass
                except Exception:
                    pass
            return results

        # Normalize into a list of dicts
        items: List[Any] = []
        containers: List[Any] = []
        containers.append(content)
        # Add additional candidates commonly used by runtimes
        if isinstance(resp, dict):
            if resp.get("metadata") is not None:
                containers.append(resp.get("metadata"))
        else:
            metadata_attr = getattr(resp, "metadata", None)
            if metadata_attr is not None:
                containers.append(metadata_attr)
        # If we got single objects with a text attribute, include that text
        if hasattr(content, "text"):
            containers.append(getattr(content, "text", None))
        if hasattr(resp, "text"):
            containers.append(getattr(resp, "text", None))

        for candidate in containers:
            if candidate is None:
                continue
            try:
                if isinstance(candidate, (dict, list)):
                    items.extend(gather_from_container(candidate))
                elif isinstance(candidate, str):
                    parsed = json.loads(candidate)
                    items.extend(gather_from_container(parsed))
            except Exception:
                continue

        # Preview for debugging shapes
        try:
            if isinstance(items, list) and items:
                preview_item = items[0]
                if isinstance(preview_item, dict):
                    preview_text = preview_item.get("text") or preview_item.get("content") or str(preview_item)
                else:
                    preview_text = str(preview_item)
                LOGGER.debug("Web tool first item preview: %s", str(preview_text)[:200])
            elif isinstance(content, str):
                LOGGER.debug("Web tool raw string content preview: %s", content[:200])
        except Exception:
            pass

        normalized: List[Dict[str, Any]] = []
        for it in items[:max_results]:
            title_val: Optional[str]
            url_val: Optional[str]
            content_val: Optional[str]

            if isinstance(it, dict):
                title_val = it.get("title") or it.get("source") or "Untitled"
                url_val = it.get("url") or it.get("source_url") or it.get("link")
                content_val = it.get("text") or it.get("content") or it.get("snippet") or it.get("description")
            else:
                title_val = getattr(it, "title", None) or getattr(it, "source", None) or "Untitled"
                url_val = getattr(it, "url", None) or getattr(it, "source_url", None) or getattr(it, "link", None)
                content_val = (
                    getattr(it, "text", None)
                    or getattr(it, "content", None)
                    or getattr(it, "snippet", None)
                    or getattr(it, "description", None)
                )

            normalized.append({"title": title_val or "Untitled", "url": url_val, "content": content_val or ""})

        if not normalized:
            # Emit a small shape hint at INFO to aid debugging
            try:
                if isinstance(content, dict):
                    LOGGER.info("Search response had no results; top-level dict keys: %s", list(content.keys()))
                elif isinstance(content, list) and content:
                    first = content[0]
                    if isinstance(first, dict):
                        LOGGER.info("Search response had no results; first list item keys: %s", list(first.keys()))
                    else:
                        LOGGER.info("Search response had no results; first list item type: %s", type(first).__name__)
                else:
                    LOGGER.info("Search response had no results; content type: %s", type(content).__name__)
            except Exception:
                pass
        LOGGER.info("Found %d results for query.", len(normalized))
        return normalized

    def summarize_results(self, query: str, results: List[Dict[str, Any]]) -> SummarizedBatch:
        """Summarize a set of web results using the LLM with citations to URLs."""
        # Build a compact source digest to stay within token limits
        digest_parts: List[str] = []
        for idx, r in enumerate(results[:8], start=1):
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            content = r.get("content", "")
            snippet = textwrap.shorten(content, width=900, placeholder="…")
            digest_parts.append(f"[{idx}] {title}\nURL: {url}\nExcerpt: {snippet}")
        digest = "\n\n".join(digest_parts)

        prompt = textwrap.dedent(
            f"""
            You are given multiple web search results for the query: "{query}".
            Write a concise, objective summary (8-12 bullets) capturing key facts, definitions, trends, and differing viewpoints.
            - Cite sources inline using reference markers like [1], [2], etc., corresponding to the numbered sources below.
            - Avoid speculation; prefer verifiable facts.
            - Return JSON with the following shape only:
              {{
                "summary_markdown": "markdown bullets with [n] citations",
                "key_points": ["point 1", "point 2", …]
              }}

            Sources:
            {digest}
            """
        ).strip()
        LOGGER.info("Summarizing %d results for query…", len(results))
        raw = self.agent.chat(prompt, temperature=0.1, max_output_tokens=1000)
        summary_markdown: str = ""
        key_points: List[str] = []
        try:
            data = json.loads(raw)
            summary_markdown = str(data.get("summary_markdown", "")).strip()
            key_points_raw = data.get("key_points") or []
            key_points = [str(p).strip() for p in key_points_raw if str(p).strip()]
        except Exception as parse_error:
            LOGGER.warning("Failed to parse summary JSON (%s). Using raw text fallback.", parse_error)
            summary_markdown = raw.strip()
            key_points = []

        return SummarizedBatch(
            query=query,
            sources=results,
            summary_markdown=summary_markdown,
            key_points=key_points,
        )

    def evaluate_sufficiency(
        self, user_question: str, batches: List[SummarizedBatch]
    ) -> Tuple[bool, str, List[str]]:
        """Ask the LLM if the collected summaries are sufficient and get optional new queries.

        Returns (is_sufficient, reason, additional_queries)
        """
        combined_points: List[str] = []
        for b in batches:
            combined_points.extend(b.key_points or [])
        combined_text = "\n".join([b.summary_markdown for b in batches])

        prompt = textwrap.dedent(
            f"""
            Consider the user's question and the summaries/key points below. Decide if we have enough information to answer thoroughly.
            Return ONLY JSON of the form:
            {{
              "sufficient": true | false,
              "reason": "short explanation",
              "additional_queries": ["q1", "q2", "q3"]
            }}

            User question: "{user_question}"

            Key points:
            - """
        ).strip()
        for p in combined_points[:20]:
            prompt += f"\n- {p}"
        prompt += "\n\nSummaries (markdown with citations):\n" + textwrap.shorten(combined_text, width=5000, placeholder="…")

        LOGGER.info("Evaluating sufficiency of collected information…")
        raw = self.agent.chat(prompt, temperature=0.0, max_output_tokens=500)
        try:
            data = json.loads(raw)
            sufficient = bool(data.get("sufficient", False))
            reason = str(data.get("reason", "")).strip()
            additional_queries_raw = data.get("additional_queries") or []
            additional_queries = [str(q).strip() for q in additional_queries_raw if str(q).strip()]
            LOGGER.info("Sufficiency=%s; reason=%s", sufficient, reason)
            return sufficient, reason, additional_queries[:3]
        except Exception as parse_error:
            LOGGER.warning("Failed to parse sufficiency JSON (%s). Assuming insufficient once.", parse_error)
            return False, "Could not parse sufficiency analysis.", []

    def compile_report(self, user_question: str, batches: List[SummarizedBatch]) -> str:
        """Ask the LLM to compile a structured report with citations."""
        sources_lines: List[str] = []
        for b in batches:
            for idx, s in enumerate(b.sources[:8], start=1):
                sources_lines.append(f"- [{idx}] {s.get('title','Untitled')} — {s.get('url','')}")
        citations = "\n".join(sources_lines)

        summaries_concat = "\n\n".join(
            [
                f"### Query: {b.query}\n\n{b.summary_markdown}" if b.summary_markdown else f"### Query: {b.query} — (no summary)"
                for b in batches
            ]
        )

        prompt = textwrap.dedent(
            f"""
            Write a concise, well-structured report answering the user's question using the collected research below.
            Requirements:
            - Include sections: Executive Summary, Findings (with subheadings), Limitations, and References.
            - Use markdown.
            - Use numeric citations like [1], [2] that map to the References list provided.
            - Be precise and avoid speculation; prefer verifiable facts.

            User question: "{user_question}"

            Research summaries:
            {summaries_concat}

            References (map [n] to these):
            {citations}
            """
        ).strip()
        LOGGER.info("Compiling final report…")
        report = self.agent.chat(prompt, temperature=0.2, max_output_tokens=1800)
        return report

    def run(self, user_question: str) -> Dict[str, Any]:
        """Run the deep search workflow end-to-end with logging and bounded iterations."""
        LOGGER.info("User question: %s", user_question)

        all_batches: List[SummarizedBatch] = []
        round_index = 0

        # Initial round + up to max_extra_rounds augmentations
        while True:
            round_index += 1
            LOGGER.info("Round %d — planning queries", round_index)
            if round_index == 1:
                queries = self.generate_diverse_queries(user_question)
            else:
                # On augment rounds, nudge LLM to refine based on gaps
                refinement_prompt = textwrap.dedent(
                    f"""
                    Based on the user's question and the existing summaries, produce three refined Google search queries
                    optimized to fill remaining gaps. Return ONLY a JSON array of strings.

                    User question: "{user_question}"
                    """
                ).strip()
                raw = self.agent.chat(refinement_prompt, temperature=0.4, max_output_tokens=300)
                try:
                    queries = json.loads(raw)
                    if not (isinstance(queries, list) and len(queries) == 3 and all(isinstance(q, str) for q in queries)):
                        raise ValueError("Expected three queries")
                except Exception:
                    # Fallback: reuse the initial generator
                    queries = self.generate_diverse_queries(user_question)
            LOGGER.info("Round %d queries: %s", round_index, queries)

            # Search + summarize each query
            for q in queries:
                results = self.tavily_search(q)
                # Log top hits
                for r in results[:5]:
                    LOGGER.info("Hit: %s — %s", r.get("title"), r.get("url"))
                batch = self.summarize_results(q, results)
                all_batches.append(batch)

            # Evaluate sufficiency
            sufficient, reason, addl_queries = self.evaluate_sufficiency(user_question, all_batches)
            if sufficient:
                LOGGER.info("Decision: sufficient. Reason: %s", reason)
                break

            if round_index - 1 >= self.max_extra_rounds:
                LOGGER.info("Decision: reached max augmentation rounds (%d). Proceeding.", self.max_extra_rounds)
                break

            LOGGER.info(
                "Decision: insufficient (reason: %s). Will augment with additional queries: %s",
                reason,
                addl_queries or "(LLM will generate)",
            )

        report = self.compile_report(user_question, all_batches)
        LOGGER.info("Report generated (%d chars)", len(report))

        return {
            "question": user_question,
            "rounds": round_index,
            "batches": [
                {
                    "query": b.query,
                    "sources": b.sources,
                    "summary_markdown": b.summary_markdown,
                    "key_points": b.key_points,
                }
                for b in all_batches
            ],
            "report_markdown": report,
        }


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%H:%M:%S",
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Deep Search Agent (Llama Stack websearch tool)")
    parser.add_argument("question", type=str, help="User question to research")
    parser.add_argument("--base-url", default=os.getenv("LLAMA_STACK_BASE_URL", "http://localhost:8321"))
    parser.add_argument("--model-id", default=os.getenv("LLAMA_STACK_MODEL_ID", "gpt-4o-mini"))
    parser.add_argument("--max-extra-rounds", type=int, default=2)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    configure_logging(args.verbose)

    LOGGER.info("Connecting to Llama Stack at %s (model=%s)", args.base_url, args.model_id)
    agent = DeepSearchAgent(
        llama_base_url=args.base_url,
        model_id=args.model_id,
        max_extra_rounds=args.max_extra_rounds,
    )

    result = agent.run(args.question)
    # Print final report to stdout
    print("\n===== Deep Search Report =====\n")
    print(result["report_markdown"])  # noqa: T201

    return 0


if __name__ == "__main__":
    sys.exit(main())


