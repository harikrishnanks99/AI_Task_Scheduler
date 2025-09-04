JSON_SCHEMA_FOR_LLM = """
The JSON must have the following structure:

{
  "task_name": "string",
  "tool_to_use": "string",
  "parameters": {{ ... }},   // tool-specific parameters
  "schedule_details": {{
    "type": "cron" | "datetime" | "interval",
    "value": {{
      // For 'cron': use ONLY for recurring tasks with specific days/times,
      //   e.g. {{ "minute": "0", "hour": "9", "day_of_week": "1", "day_of_month": "*", "month_of_year": "*" }}
      // For 'datetime': use ONLY for a one-time event at a specific date/time,
      //   e.g. {{ "year": 2025, "month": 10, "day": 25, "hour": 18, "minute": 30 }}
      // For 'interval': use ONLY for "every N units" style repetition,
      //   e.g. {{ "every": 1, "period": "hours" }}
    }}
  }}
}}
"""

def get_step1_reasoning_prompt(prompt: str, timezone: str, tools: list[str]) -> str:
    """Generates the reasoning prompt for the LLM (step 1)."""
    return f"""
Analyze the user's request and extract the key information.

1.  **Task Name:** A short name for the task.
2.  **Tool:** Choose the single best tool from the `Available Tools` list.
3.  **Parameters:** List the required parameters for the chosen tool.
    - For `send_email`, the parameters are: `recipient`, `subject`, and `body`.
    - For `scrape_web`: `url`, and a CSS `selector` (e.g., 'h1', '.article-title', 'div#main-content p'). If the user just says "headlines" or "links", you can infer a common selector like 'h2' or 'a'.
    - For `call_api`, the parameters are: `endpoint`, `payload`.
4.  **Schedule:** Describe the schedule.

---
- **Available Tools:** {tools}
- **User's Timezone:** {timezone}
- **User's Request:** "{prompt}"
---
**Analysis:**
"""

def get_step2_formatting_prompt(analysis_text: str) -> str:
    """
    Step 2: Converts LLM analysis into a strictly validated JSON object
    with structured schedule_details.value.
    """
    return f"""
Convert the following analysis into a valid JSON object following these rules:

1. The JSON must include:
   - "task_name": string
   - "tool_to_use": string (one of the available tools)
   - "parameters": object (use exact keys from the analysis)
   - "schedule_details": object with:
       - "type": "cron" | "datetime" | "interval"
       - "value": structured dictionary depending on type

2. Schedule details formatting:

   - If "type" is "datetime":
     - "value" must be a dictionary:
       {{
         "year": <YYYY>,
         "month": <MM>,
         "day": <DD>,
         "hour": <HH>,
         "minute": <MM>
       }}
     - Do NOT output a plain string timestamp.
   
   - If "type" is "cron":
     - "value" must be a dictionary:
       {{
         "minute": "*",
         "hour": "*",
         "day_of_week": "*",
         "day_of_month": "*",
         "month_of_year": "*"
       }}

   - If "type" is "interval":
     - "value" must be a dictionary:
       {{
         "every": <integer>,
         "period": "seconds" | "minutes" | "hours" | "days"
       }}

3. The `parameters` object MUST use the correct key names exactly as described in the analysis.
4. The `tool_to_use` MUST match one of the available tools.
5. Output only valid JSON, without extra text, explanation, or timezone field.

---
Analysis to Convert:
{analysis_text}
---
JSON Output:
"""
