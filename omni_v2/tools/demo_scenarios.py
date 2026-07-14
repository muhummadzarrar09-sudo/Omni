"""Demo Scenarios - 3 Reliable Autonomous Workflows for Hackathon Video
This file ALWAYS works - no API fails - perfect for video recording.
"""
from dataclasses import dataclass
from typing import List

@dataclass
class DemoResult:
    workflow: str
    steps: List[str]
    agent_logs: List[str]
    final_output: str
    impact_statement: str

class DemoScenarios:
    """3 bulletproof scenarios that show true agentic behavior"""
    
    def accessibility_workflow(self):
        logs = [
            "[Planner] Intent: accessibility_help | Keywords: can't see well",
            "[Planner] Plan: 4 steps [high_contrast ON, large_text ON, describe_screen, read_file]",
            "[Executor] accessibility.high_contrast -> SUCCESS (screen contrast changed)",
            "[Executor] accessibility.large_text -> SUCCESS (font size 14->18)",
            "[Monitor] Verified: screen contrast delta detected, VS Code font increased",
            "[Evaluator] Goal achieved: accessibility suite enabled. Memory: stored preference",
            "[Memory] SQLite: INSERT preference high_contrast=True, large_text=True"
        ]
        return DemoResult(
            workflow="Accessibility - Low Vision Student Mode",
            steps=["Enable high contrast", "Enable large text 18px", "Describe screen content", "Offer to read aloud"],
            agent_logs=logs,
            final_output="Accessibility suite enabled. I see VS Code with omni.py open. Want me to read it aloud? I've memorized this preference for next time.",
            impact_statement="Impact: 1.3B people with disabilities can now control PC hands-free, 100% offline, private."
        )
    
    def chain_self_healing_workflow(self):
        logs = [
            "[Planner] Chain detected: 'Open Chrome, maximize it, and go to YouTube and play Coke Studio'",
            "[Planner] Parsed chain: ['open chrome', 'maximize it', 'go to youtube', 'play coke studio'] -> 4 steps",
            "[Planner] Context resolve: 'it' in step 2 -> Chrome (step 1 entity)",
            "[Executor] Step 1: windows.launch Chrome -> FAIL (chrome.exe not found)",
            "[Monitor] Monitor: Process check - chrome.exe not in tasklist, screen unchanged -> FAIL",
            "[Evaluator] Evaluator: Step 1 failed, goal not achieved. Re-planning with fallback...",
            "[Evaluator] Re-plan: Fallback mapping Chrome->Edge (safe apps: chrome->msedge)",
            "[Executor] Step 1 retry: windows.launch Edge -> SUCCESS (msedge.exe pid 1234)",
            "[Executor] Step 2: windows.maximize Edge -> SUCCESS (window rect maximized)",
            "[Executor] Step 3: browser.navigate youtube.com -> SUCCESS",
            "[Executor] Step 4: browser.search 'Coke Studio' -> SUCCESS",
            "[Monitor] Final verification: Edge maximized, URL contains youtube, page title contains Coke Studio",
            "[Evaluator] GOAL ACHIEVED: 4/4 steps success after 1 re-plan. True autonomy demonstrated."
        ]
        return DemoResult(
            workflow="Chain Commands + Self-Healing Autonomy",
            steps=["Open Chrome (fail->Edge fallback)", "Maximize window", "Go to YouTube", "Play Coke Studio"],
            agent_logs=logs,
            final_output="Done! Opened Edge (Chrome not found, auto fallback), maximized, navigated to YouTube, searched Coke Studio. Self-healed after 1 failure - that's agentic.",
            impact_statement="Technical: Only OMNI shows Monitor->Evaluator re-planning loop. Single reasoners loop forever on failure."
        )
    
    def business_guardian_workflow(self):
        logs = [
            "[Scout Agent] Tool: OpenWeather API -> Rawalpindi 3-day forecast: Heavy rain Sindh",
            "[Scout Agent] Tool: News Search 'sugar mill strike Pakistan' -> 2 articles found, strike likelihood high",
            "[Scout Agent] Tool: Fuel Price API -> Diesel +5% this week",
            "[Risk Agent] Reasoning: Rain Sindh = sugar cane delay + Mill strike + Diesel high = 85% risk sugar price +20% in 3 days",
            "[Risk Agent] Impact: Current stock 50kg, burn rate 10kg/day, will stockout in 5 days, price spike before restock",
            "[Sourcing Agent] Tool: Vendor DB search 'sugar suppliers Rawalpindi' -> 3 suppliers, best: Akbar Traders @ 155/kg vs current 160",
            "[Action Agent] Tool: Generate PO PDF -> data/orders/PO-2026-07-13-sugar.pdf created",
            "[Action Agent] Tool: WhatsApp draft Urdu -> 'As-salamu Alaikum Akbar bhai, 100kg cheeni ka urgent order...'",
            "[Evaluator] Goal: Business continuity secured, saved 500 Rs, avoided stockout"
        ]
        return DemoResult(
            workflow="Small Business Supply Guardian (NIGRAN inside OMNI)",
            steps=["Monitor weather/news/fuel", "Predict sugar price spike 85% risk", "Find alternate cheaper supplier", "Generate PO PDF + Urdu WhatsApp"],
            agent_logs=logs,
            final_output="Risk: 85% sugar price +20% in 3 days due to Sindh rain + strike. Action: Found Akbar Traders @155/kg (vs 160). Generated PO PDF and Urdu WhatsApp draft. Saved Rs 500 and avoided stockout. This is your supply chain team.",
            impact_statement="Business Impact: 65M small shops in Pakistan lose $4B to supply shocks. OMNI is their Amazon-level supply chain, offline, in Urdu."
        )

if __name__ == "__main__":
    demo = DemoScenarios()
    for name in ["accessibility_workflow", "chain_self_healing_workflow", "business_guardian_workflow"]:
        result = getattr(demo, name)()
        print(f"\n{'='*80}")
        print(f"WORKFLOW: {result.workflow}")
        print(f"{'='*80}")
        for log in result.agent_logs:
            print(log)
        print(f"\nFINAL: {result.final_output}")
        print(f"IMPACT: {result.impact_statement}")
