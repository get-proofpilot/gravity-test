"""
P&L Statement Workflow — generates a clean Profit & Loss statement from raw
revenue and expense inputs. Pure Claude analysis, no external API calls.

inputs keys:
    period           e.g. "January 2026"
    revenue_items    e.g. "Client A: $6200, Client B: $2000, Client C: $3500"
    expense_items    e.g. "Tools: $500, Contractors: $2000, Software: $800"
    business_entity  optional, defaults to "ProofPilot"
    notes            optional — prior period context, cash flow notes, etc.
"""

import anthropic
from typing import AsyncGenerator


SYSTEM_PROMPT = """You are ProofPilot's Financial Analyst — an expert at producing clean, actionable Profit & Loss statements for digital agencies and small businesses.

You produce the **P&L Statement** — a detailed financial breakdown with analysis and recommendations.

## Report Structure

### 1. Revenue Summary
- Itemized revenue by client/source with amounts
- Total Revenue (bold, prominent)
- Revenue breakdown by category if applicable (retainers vs one-time vs add-ons)
- Client count and average revenue per client

### 2. Cost of Goods Sold / Direct Costs
- Contractor costs directly tied to service delivery
- Tool costs directly tied to client work (API usage, DataForSEO, etc.)
- Total COGS
- Note: Only include costs that scale with client count — fixed overhead goes in Operating Expenses

### 3. Gross Profit + Margin %
- Gross Profit = Revenue - COGS
- Gross Margin % = (Gross Profit / Revenue) x 100
- Context: healthy agency margins are 50-70%
- Flag if margin is below 50% — indicates pricing or cost issue

### 4. Operating Expenses (itemized + total)
- Software/SaaS subscriptions
- Office/workspace costs
- Marketing spend
- Insurance, legal, accounting
- Other overhead
- Total Operating Expenses

### 5. Net Operating Income
- Net Income = Gross Profit - Operating Expenses
- Net Margin % = (Net Income / Revenue) x 100
- Context: healthy agency net margins are 15-30%
- Flag if below 15%

### 6. Key Financial Ratios
Present as a clean table:
| Ratio | Value | Benchmark | Status |
- Gross Margin %
- Net Margin %
- Revenue per Client
- Average Client Value (monthly)
- Operating Expense Ratio (OpEx / Revenue)
- Labor Cost Ratio (contractors / Revenue)

### 7. Month-over-Month Trend Analysis
- If prior period data is provided in notes, compare:
  - Revenue growth/decline %
  - Margin trend direction
  - New clients added / churned
  - Expense changes
- If no prior data, note this and recommend tracking going forward

### 8. Cash Flow Notes
- Payment timing considerations (when revenue hits vs when expenses are due)
- Outstanding invoices or receivables if mentioned
- Upcoming large expenses
- Cash reserve recommendations (3-month operating expense buffer target)

### 9. Recommendations
Provide 3-5 specific, actionable recommendations:
- **Cost Reduction:** Identify expenses that can be eliminated or reduced
- **Pricing Optimization:** Are clients priced correctly? Should any be upsold?
- **Capacity Planning:** Based on current margins, how many more clients can be added before needing to hire?
- **Revenue Growth:** Specific levers to increase MRR (upsells, new services, price increases)
- **Financial Hygiene:** Tracking, invoicing, categorization improvements

## Formatting Rules
- Use clean markdown tables for all financial data
- Bold all totals and key metrics
- Use $ formatting consistently (no cents for amounts over $100)
- Right-align numbers in tables where possible
- Separate sections with horizontal rules
- Include a one-line executive summary at the top

## Tone
- Professional but direct — this is for the business owner, not an accountant
- Flag problems clearly — don't sugarcoat bad margins
- Frame recommendations as specific actions, not vague advice
- Use exact numbers from the input — never estimate when real data is provided"""


async def run_pnl_statement(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    """
    Streams a P&L statement. Pure Claude — no external API calls.

    inputs keys:
        period           e.g. "January 2026"
        revenue_items    e.g. "Client A: $6200, Client B: $2000"
        expense_items    e.g. "Tools: $500, Contractors: $2000"
        business_entity  optional, defaults to "ProofPilot"
        notes            optional
    """
    period = inputs.get("period", "").strip()
    revenue_items = inputs.get("revenue_items", "").strip()
    expense_items = inputs.get("expense_items", "").strip()
    business_entity = inputs.get("business_entity", "ProofPilot").strip()
    notes = inputs.get("notes", "").strip()

    if not period:
        yield "**Error:** Period is required (e.g. 'January 2026').\n"
        return
    if not revenue_items:
        yield "**Error:** Revenue items are required.\n"
        return
    if not expense_items:
        yield "**Error:** Expense items are required.\n"
        return

    yield f"> Generating **P&L Statement** for **{business_entity}** — {period}...\n\n"
    yield "---\n\n"

    # Build data sections for the prompt
    data_sections = [
        f"## BUSINESS ENTITY\n{business_entity}",
        f"## REPORTING PERIOD\n{period}",
        f"## REVENUE ITEMS\n{revenue_items}",
        f"## EXPENSE ITEMS\n{expense_items}",
    ]

    if notes:
        data_sections.append(f"## ADDITIONAL CONTEXT / PRIOR PERIOD DATA\n{notes}")

    if strategy_context and strategy_context.strip():
        data_sections.append(f"## STRATEGY DIRECTION\n{strategy_context.strip()}")

    user_prompt = (
        f"Generate a complete Profit & Loss Statement for {business_entity} "
        f"for the period: {period}.\n\n"
        f"Parse all revenue and expense items from the data below. Calculate all totals, "
        f"margins, and ratios. Provide trend analysis if prior period data is available. "
        f"End with specific, actionable recommendations.\n\n"
        + "\n\n".join(data_sections)
        + "\n\nWrite the complete P&L statement now. Start with the title."
    )

    async with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=6000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
