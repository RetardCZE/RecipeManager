TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "retrieve_ingredient",
            "description": "Semantic search for ingredients that match a free‑text description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "User‑provided ingredient description"},
                    "k": {"type": "integer", "description": "Max results", "default": 5},
                },
                "required": ["description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "retrieve_meal",
            "description": "Find meals that match a free‑text description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "k": {"type": "integer", "default": 5},
                },
                "required": ["description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "retrieve_meal_by_instructions",
            "description": "Find meals similar to given cooking instructions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instructions": {"type": "string"},
                    "k": {"type": "integer", "default": 5},
                },
                "required": ["instructions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_ingredients",
            "description": "Return the full ingredient catalogue.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price",
            "description": "Look up current price & sale status for an ingredient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ingredient_id": {"type": "integer"},
                },
                "required": ["ingredient_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_basket",
            "description": "Add an ingredient (optionally multiple) to the active basket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ingredient_id": {"type": "integer"},
                    "qty": {"type": "integer", "default": 1},
                },
                "required": ["ingredient_id"],
            },
        },
    },
]

# ------------------------------------------------ SALE + DB helpers
SALE_AND_DB_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_sale_items",
            "description": "Return every ingredient that is currently on sale.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "retrieve_meals_with_sale_overlap",
            "description":
               "Find meals that share at least `min_overlap` sale ingredients, "
               "sorted by overlap count descending.",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_overlap": {"type": "integer", "default": 1},
                    "k": {"type": "integer", "default": 10},
                },
                "required": ["min_overlap"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_meal_details",
            "description": "Return id, name, category, area, description & instructions for a meal.",
            "parameters": {
                "type": "object",
                "properties": {"meal_id": {"type": "integer"}},
                "required": ["meal_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_meal_ingredients",
            "description":
               "List each ingredient (name, measure) plus price/discount for a meal.",
            "parameters": {
                "type": "object",
                "properties": {"meal_id": {"type": "integer"}},
                "required": ["meal_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ingredient_details",
            "description": "Fetch full metadata (name, description, type) for one ingredient.",
            "parameters": {
                "type": "object",
                "properties": {"ingredient_id": {"type": "integer"}},
                "required": ["ingredient_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_meal_to_basket",
            "description":
               "Add every shop‑listed ingredient of a meal to the basket, "
               "optionally scaled for extra servings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "meal_id": {"type": "integer"},
                    "servings": {"type": "integer", "default": 1},
                },
                "required": ["meal_id"],
            },
        },
    },
]

TOOL_SCHEMAS.extend(SALE_AND_DB_SCHEMAS)