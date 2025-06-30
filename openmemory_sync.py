"""
openmemory_sync.py

Federated strategy learning system for Kai_WebNavigator.
Enables sharing and merging of successful selector strategies across AI agents.

Trust Protocol: Weighted merging based on success rate, confidence, and contributor reputation.
"""

import json
from pathlib import Path
from copy import deepcopy
from datetime import datetime

class OpenMemorySync:
    def __init__(self, shared_drive_path, agent_id="kai"):
        self.shared_path = Path(shared_drive_path)
        self.agent_id = agent_id
        self.master_index_file = self.shared_path / "master_index.json"
        self.trust_config = {
            "min_confidence_threshold": 0.7,
            "min_attempts_threshold": 3,
            "max_merge_weight": 0.8,  # Prevent remote data from overwhelming local
            "default_reputation": 1.0
        }

    def evaluate_strategy_quality(self, strategy_entry):
        """Calculate composite trust score for a strategy entry."""
        attempts = strategy_entry.get("success", 0) + strategy_entry.get("fail", 0)
        if attempts == 0:
            return 0.0
        
        success_rate = strategy_entry.get("success", 0) / attempts
        confidence = min(attempts / self.trust_config["min_attempts_threshold"], 1.0)
        reputation = strategy_entry.get("reputation", self.trust_config["default_reputation"])
        
        quality_score = success_rate * confidence * reputation
        return min(quality_score, 1.0)

    def load_master_index(self):
        """Load master index with contributor metadata."""
        if self.master_index_file.exists():
            with open(self.master_index_file, 'r') as f:
                return json.load(f)
        return {
            "contributors": {},
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "trust_scores": {}
        }

    def save_master_index(self, index_data):
        """Save updated master index."""
        index_data["last_updated"] = datetime.utcnow().isoformat() + "Z"
        self.shared_path.mkdir(parents=True, exist_ok=True)
        with open(self.master_index_file, 'w') as f:
            json.dump(index_data, f, indent=2)

    def pull_remote_stats(self, domain):
        """Download and validate strategy stats for a specific domain."""
        domain_file = self.shared_path / f"{domain.replace('.', '_')}_strategy_stats.json"
        
        if not domain_file.exists():
            print(f"🌐 No remote stats found for {domain}")
            return {}

        try:
            with open(domain_file, 'r') as f:
                remote_data = json.load(f)
            
            # Validate and filter by quality
            validated_data = self._validate_remote_data(remote_data, domain)
            print(f"🌐 Pulled {len(validated_data)} high-quality strategies for {domain}")
            return validated_data
            
        except Exception as e:
            print(f"⚠️ Failed to load remote stats for {domain}: {e}")
            return {}

    def _validate_remote_data(self, remote_data, domain):
        """Filter remote data by trust thresholds."""
        validated = {}
        
        for intent, strategies in remote_data.get(domain, {}).items():
            validated_strategies = {}
            
            for strategy_name, strategy_data in strategies.items():
                quality_score = self.evaluate_strategy_quality(strategy_data)
                
                if quality_score >= self.trust_config["min_confidence_threshold"]:
                    strategy_data["quality_score"] = quality_score
                    strategy_data["contributor"] = strategy_data.get("contributor", "unknown")
                    validated_strategies[strategy_name] = strategy_data
                    print(f"✅ Validated {strategy_name}: {quality_score:.2f} quality")
                else:
                    print(f"❌ Rejected {strategy_name}: {quality_score:.2f} quality (below {self.trust_config['min_confidence_threshold']})")
            
            if validated_strategies:
                validated[intent] = validated_strategies
        
        return {domain: validated} if validated else {}

    def merge_with_local_stats(self, local_stats, remote_stats):
        """Merge remote strategies with local data using weighted averaging."""
        merged = deepcopy(local_stats)
        
        for domain, domain_data in remote_stats.items():
            if domain not in merged:
                merged[domain] = {}
            
            for intent, strategies in domain_data.items():
                if intent not in merged[domain]:
                    merged[domain][intent] = {}
                
                for strategy_name, remote_strategy in strategies.items():
                    if strategy_name in merged[domain][intent]:
                        # Weighted merge of existing strategy
                        local_strategy = merged[domain][intent][strategy_name]
                        merged_strategy = self._weighted_merge_strategy(local_strategy, remote_strategy)
                        merged[domain][intent][strategy_name] = merged_strategy
                        print(f"🔀 Merged {strategy_name} for {domain}/{intent}")
                    else:
                        # Add new strategy from remote
                        merged[domain][intent][strategy_name] = remote_strategy
                        print(f"➕ Added remote strategy {strategy_name} for {domain}/{intent}")
        
        return merged

    def _weighted_merge_strategy(self, local, remote):
        """Merge two strategy entries with weighted averaging."""
        local_quality = self.evaluate_strategy_quality(local)
        remote_quality = self.evaluate_strategy_quality(remote)
        
        # Calculate merge weights based on quality scores
        total_quality = local_quality + remote_quality
        if total_quality == 0:
            return local  # Fallback to local if both have zero quality
        
        local_weight = local_quality / total_quality
        remote_weight = remote_quality / total_quality
        
        # Cap remote influence
        remote_weight = min(remote_weight, self.trust_config["max_merge_weight"])
        local_weight = 1.0 - remote_weight
        
        # Weighted average of success/fail counts
        merged = {
            "success": int(local.get("success", 0) * local_weight + remote.get("success", 0) * remote_weight),
            "fail": int(local.get("fail", 0) * local_weight + remote.get("fail", 0) * remote_weight),
            "last_merge": datetime.utcnow().isoformat() + "Z",
            "contributors": list(set([self.agent_id] + remote.get("contributors", [remote.get("contributor", "unknown")])))
        }
        
        return merged

    def publish_discoveries(self, local_stats, domain):
        """Share high-quality local discoveries to the shared repository."""
        domain_data = local_stats.get(domain, {})
        if not domain_data:
            print(f"📤 No local data to publish for {domain}")
            return

        # Filter for high-quality strategies only
        publishable = {}
        for intent, strategies in domain_data.items():
            quality_strategies = {}
            for strategy_name, strategy_data in strategies.items():
                quality_score = self.evaluate_strategy_quality(strategy_data)
                
                if quality_score >= self.trust_config["min_confidence_threshold"]:
                    strategy_data["contributor"] = self.agent_id
                    strategy_data["published_at"] = datetime.utcnow().isoformat() + "Z"
                    quality_strategies[strategy_name] = strategy_data
            
            if quality_strategies:
                publishable[intent] = quality_strategies

        if publishable:
            # Save to shared domain file
            domain_file = self.shared_path / f"{domain.replace('.', '_')}_strategy_stats.json"
            existing_data = {}
            
            if domain_file.exists():
                with open(domain_file, 'r') as f:
                    existing_data = json.load(f)
            
            # Merge with existing shared data
            merged_shared = self.merge_with_local_stats(existing_data, {domain: publishable})
            
            # Save updated shared file
            self.shared_path.mkdir(parents=True, exist_ok=True)
            with open(domain_file, 'w') as f:
                json.dump(merged_shared, f, indent=2)
            
            # Update master index
            index = self.load_master_index()
            if self.agent_id not in index["contributors"]:
                index["contributors"][self.agent_id] = {
                    "first_contribution": datetime.utcnow().isoformat() + "Z",
                    "domains_contributed": []
                }
            
            if domain not in index["contributors"][self.agent_id]["domains_contributed"]:
                index["contributors"][self.agent_id]["domains_contributed"].append(domain)
            
            index["contributors"][self.agent_id]["last_contribution"] = datetime.utcnow().isoformat() + "Z"
            self.save_master_index(index)
            
            print(f"📤 Published {len(publishable)} high-quality strategies for {domain}")
        else:
            print(f"📤 No strategies met quality threshold for publishing to {domain}")