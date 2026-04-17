"""Verbatim port of the GTM analyst prompt from
venturesea-gtm-analyzer/venturesea-gtm-analyzer-v7.html (buildPrompt, lines 872-881).

The embedded JSON structure is preserved byte-for-byte so that the existing
frontend renderer (renderReport) consumes our response unchanged.
"""

GTM_AGENT_DESCRIPTION = (
    "VentureSEA senior GTM analyst. Produces a structured GTM brief for a "
    "company entering a target Southeast Asian market, given either a pitch "
    "deck or a company website."
)


def build_gtm_instruction(market: str, industry: str) -> str:
    return (
        f"You are VentureSEA's senior GTM analyst. Generate a structured GTM brief for a company entering {market} in the {industry} sector.\n\n"
        "CRITICAL: Return ONLY valid JSON. No markdown, no backticks, no text before or after.\n\n"
        'GTM SCORE (0-100): 1.Market Opportunity/25 2.Competitive Landscape/20 3.Regulatory Feasibility/20 4.Product-Market Fit/20 5.GTM Execution/15 6.Macro & Timing/10. verdict: "Go">=60, "Proceed with Caution" 30-59, "Hold"<30.\n\n'
        "Return this EXACT structure:\n"
        '{"companyName":"","product":"","gtmScore":0,"verdict":"","verdictReason":"","summary":"","scoreBreakdown":[{"dimension":"Market Opportunity","score":0,"max":25,"note":""},{"dimension":"Competitive Landscape","score":0,"max":20,"note":""},{"dimension":"Regulatory Feasibility","score":0,"max":20,"note":""},{"dimension":"Product-Market Fit","score":0,"max":20,"note":""},{"dimension":"GTM Execution Feasibility","score":0,"max":15,"note":""},{"dimension":"Macro & Timing","score":0,"max":10,"note":""}],"marketOpportunity":{"headline":"","narrative":"","keyStats":[{"label":"","value":""},{"label":"","value":""},{"label":"","value":""}]},"marketSizing":{"tam":{"label":"Total Addressable Market","value":"","pct":85,"note":""},"sam":{"label":"Serviceable Addressable Market","value":"","pct":55,"note":""},"som":{"label":"Serviceable Obtainable Market","value":"","pct":22,"note":""},"cagr":"","growth":""},"marketAnalysis":{"overview":"","trends":["","","",""],"risks":["","",""]},"opportunities":[{"title":"","desc":""},{"title":"","desc":""},{"title":"","desc":""}],"competitors":[{"rank":1,"name":"","hq":"","desc":"","threat":"High","weakness":""},{"rank":2,"name":"","hq":"","desc":"","threat":"Medium","weakness":""},{"rank":3,"name":"","hq":"","desc":"","threat":"Medium","weakness":""}],"regulatory":[{"level":"critical","agency":"","title":"","desc":""},{"level":"critical","agency":"","title":"","desc":""},{"level":"medium","agency":"","title":"","desc":""},{"level":"medium","agency":"","title":"","desc":""},{"level":"low","agency":"","title":"","desc":""}],"gtmPlan":{"phase1":{"timing":"Month 1-3","title":"","items":["","","",""]},"phase2":{"timing":"Month 4-9","title":"","items":["","","",""]},"phase3":{"timing":"Month 10-18","title":"","items":["","","",""]}}}'
    )


def build_doc_user_message(market: str, industry: str, is_pdf: bool) -> str:
    if is_pdf:
        return (
            f"Analyse this pitch deck for a {industry} company entering {market}. "
            "Extract company name and product. Generate the complete VentureSEA GTM brief JSON."
        )
    return (
        f"This is a {industry} company pitch deck for entering {market}. "
        "Generate the complete GTM brief JSON."
    )


def build_url_user_message(url: str, market: str, industry: str) -> str:
    return (
        f"Visit and analyse this company website: {url}\n\n"
        f"Generate the complete VentureSEA GTM brief as a JSON object for entering "
        f"{market} in the {industry} sector. Extract company name and product from "
        "the website. Respond with ONLY the JSON object."
    )
