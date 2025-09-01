book_resrervation_tool = {
    "type": "function",
    "name": "book_reservation",
    "description": "Book a reservation.",
    "parameters": {
        "properties": {
            "user_id": {
                "title": "User Id",
                "type": "string"
            },
            "origin": {
                "title": "Origin",
                "type": "string"
            },
            "destination": {
                "title": "Destination",
                "type": "string"
            },
            "flight_type": {
                "enum": [
                    "round_trip",
                    "one_way"
                ],
                "title": "Flight Type",
                "type": "string"
            },
            "cabin": {
                "enum": [
                    "business",
                    "economy",
                    "basic_economy"
                ],
                "title": "Cabin",
                "type": "string"
            },
            "flights": {
                "items": {
                    "properties": {
                        "flight_number": {
                            "description": "Flight number, such as 'HAT001'.",
                            "title": "Flight Number",
                            "type": "string"
                        },
                        "date": {
                            "description": "The date for the flight in the format 'YYYY-MM-DD', such as '2024-05-01'.",
                            "title": "Date",
                            "type": "string"
                        }
                    },
                    "required": [
                        "flight_number",
                        "date"
                    ],
                    "title": "FlightInfo",
                    "type": "object"
                },
                "title": "Flights",
                "type": "array"
            },
            "passengers": {
                "items": {
                    "properties": {
                        "first_name": {
                            "description": "Passenger's first name",
                            "title": "First Name",
                            "type": "string"
                        },
                        "last_name": {
                            "description": "Passenger's last name",
                            "title": "Last Name",
                            "type": "string"
                        },
                        "dob": {
                            "description": "Date of birth in YYYY-MM-DD format",
                            "title": "Dob",
                            "type": "string"
                        }
                    },
                    "required": [
                        "first_name",
                        "last_name",
                        "dob"
                    ],
                    "title": "Passenger",
                    "type": "object"
                },
                "title": "Passengers",
                "type": "array"
            },
            "payment_methods": {
                "items": {
                    "properties": {
                        "payment_id": {
                            "description": "Unique identifier for the payment",
                            "title": "Payment Id",
                            "type": "string"
                        },
                        "amount": {
                            "description": "Payment amount in dollars",
                            "title": "Amount",
                            "type": "integer"
                        }
                    },
                    "required": [
                        "payment_id",
                        "amount"
                    ],
                    "title": "Payment",
                    "type": "object"
                },
                "title": "Payment Methods",
                "type": "array"
            },
            "total_baggages": {
                "title": "Total Baggages",
                "type": "integer"
            },
            "nonfree_baggages": {
                "title": "Nonfree Baggages",
                "type": "integer"
            },
            "insurance": {
                "enum": [
                    "yes",
                    "no"
                ],
                "title": "Insurance",
                "type": "string"
            }
        },
        "required": [
            "user_id",
            "origin",
            "destination",
            "flight_type",
            "cabin",
            "flights",
            "passengers",
            "payment_methods",
            "total_baggages",
            "nonfree_baggages",
            "insurance"
        ],
        "type": "object"
    }
}