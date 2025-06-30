"""
strategy_scorer.py

Tracks strategy success/failure rates and dynamically reorders fallbacks
based on historical performance per domain + intent.

Integrates with log_writer.py and memory.json to build performance intelligence.
"""

import json
from pathlib import Path
from copy import deepcopy

class StrategyScorer:
    def __init__(self, stats_file):
        self.stats_file = Path(stats_file)
        self.stats = self._load_stats()

    def _load_stats(self):
        """Load strategy statistics from JSON file."""
        if self.stats_file.exists():
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_stats(self):
        """Save strategy statistics to JSON file."""
        self.stats_file.parent.mkdir(exist_ok=True)
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)

    def record_result(self, domain, intent, strategy, success):
        """Record success/failure for a strategy on a specific domain + intent."""
        if domain not in self.stats:
            self.stats[domain] = {}
        if intent not in self.stats[domain]:
            self.stats[domain][intent] = {}
        if strategy not in self.stats[domain][intent]:
            self.stats[domain][intent][strategy] = {"success": 0, "fail": 0}

        # Increment appropriate counter
        if success:
            self.stats[domain][intent][strategy]["success"] += 1
            print(f"📈 Recorded success for '{strategy}' on {domain}/{intent}")
        else:
            self.stats[domain][intent][strategy]["fail"] += 1
            print(f"📉 Recorded failure for '{strategy}' on {domain}/{intent}")

        self._save_stats()

    def calculate_scores(self, domain, intent):
        """Calculate success rates for all strategies on domain + intent."""
        if domain not in self.stats or intent not in self.stats[domain]:
            return {}

        scores = {}
        for strategy, stats in self.stats[domain][intent].items():
            total = stats["success"] + stats["fail"]
            if total > 0:
                success_rate = stats["success"] / total
                confidence = min(total / 10.0, 1.0)  # Higher confidence with more data
                weighted_score = success_rate * confidence
                scores[strategy] = {
                    "success_rate": success_rate,
                    "confidence": confidence,
                    "weighted_score": weighted_score,
                    "total_attempts": total
                }

        return scores

    def reorder_fallbacks(self, intent_data, domain, intent_name):
        """Reorder fallback strategies based on historical performance."""
        scores = self.calculate_scores(domain, intent_name)
        if not scores:
            print(f"📊 No scoring data for {domain}/{intent_name}, using original order")
            return intent_data

        # Create a copy to avoid modifying original
        reordered_intent = deepcopy(intent_data)
        fallbacks = reordered_intent.get("fallbacks", [])
        
        if not fallbacks:
            return reordered_intent

        # Score each fallback and sort by weighted score
        scored_fallbacks = []
        for fallback in fallbacks:
            method = fallback["method"]
            fallback_key = f"fallback: {method}"
            
            if fallback_key in scores:
                score_data = scores[fallback_key]
                scored_fallbacks.append({
                    "fallback": fallback,
                    "score": score_data["weighted_score"],
                    "success_rate": score_data["success_rate"],
                    "attempts": score_data["total_attempts"]
                })
                print(f"📊 {method}: {score_data['success_rate']:.1%} success ({score_data['total_attempts']} attempts)")
            else:
                # New/unscored strategies get neutral score
                scored_fallbacks.append({
                    "fallback": fallback,
                    "score": 0.5,  # Neutral score for untested strategies
                    "success_rate": 0.5,
                    "attempts": 0
                })

        # Sort by score (highest first)
        scored_fallbacks.sort(key=lambda x: x["score"], reverse=True)
        
        # Extract reordered fallbacks
        reordered_intent["fallbacks"] = [item["fallback"] for item in scored_fallbacks]
        
        print(f"🔄 Reordered fallbacks for {domain}/{intent_name} by performance")
        return reordered_intent

    def get_top_strategies(self, domain, intent_name, limit=3):
        """Get the top performing strategies for a domain + intent."""
        scores = self.calculate_scores(domain, intent_name)
        if not scores:
            return []

        # Sort by weighted score and return top strategies
        sorted_strategies = sorted(
            scores.items(), 
            key=lambda x: x[1]["weighted_score"], 
            reverse=True
        )
        
        return sorted_strategies[:limit]

    def get_domain_summary(self, domain):
        """Get performance summary for all intents on a domain."""
        if domain not in self.stats:
            return {}

        summary = {}
        for intent, strategies in self.stats[domain].items():
            total_success = sum(stats["success"] for stats in strategies.values())
            total_attempts = sum(stats["success"] + stats["fail"] for stats in strategies.values())
            
            if total_attempts > 0:
                overall_rate = total_success / total_attempts
                summary[intent] = {
                    "success_rate": overall_rate,
                    "total_attempts": total_attempts,
                    "strategies_tested": len(strategies)
                }

        return summary