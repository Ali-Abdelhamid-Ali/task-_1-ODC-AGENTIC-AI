tool_SQL = [
    {
        "type": "function",
        "function": {
            "name": "run_sql_query",
            "description": "Run a read-only SQL query on the analytics database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "A safe, read-only SQL SELECT statement."
                    }
                },
                "required": ["sql"]
            },
        },
    }
]