"""
selector_strategy.py

Enhanced SelectorStrategy that prioritizes previously successful selectors
and learns from past interactions to improve future performance.
"""

class SelectorStrategy:
    def __init__(self, page, memory_interface=None):
        self.page = page
        self.memory = memory_interface

    async def find_element_by_intent(self, intent_data, domain=None, intent_name=None):
        """Attempts layered strategy with memory-based prioritization."""
        
        timeout = intent_data.get("timeout", 3000)
        supported_methods = {"aria-label", "xpath", "text-contains"}
        
        # 🧠 Memory-based strategy prioritization
        if self.memory and domain and intent_name:
            remembered = self.memory.get(domain, intent_name)
            if remembered:
                strategy_type = remembered['successful_selector']
                print(f"🧠 Prioritizing remembered strategy: {strategy_type}")
                
                # Try remembered strategy first
                element = await self._try_remembered_strategy(intent_data, strategy_type, timeout)
                if element:
                    return element, f"memory: {strategy_type}"

        # Standard primary selector attempt
        try:
            print(f"🔍 Trying primary selector: {intent_data['primary_selector']}")
            element = await self.page.wait_for_selector(intent_data['primary_selector'], timeout=timeout)
            return element, "primary_selector"
        except:
            print("⚠️ Primary selector failed, checking fallbacks...")

        # Fallback strategies
        for fallback in intent_data.get("fallbacks", []):
            method = fallback["method"]
            value = fallback["value"]
            
            if method not in supported_methods:
                print(f"❌ Unsupported method: {method}")
                continue
            
            try:
                element = await self._try_fallback_method(method, value, timeout)
                if element:
                    print(f"✅ Found element using {method}: {value}")
                    return element, f"fallback: {method}"
                    
            except Exception as e:
                print(f"⚠️ {method} fallback failed for '{value}': {str(e)[:50]}...")
                continue
        
        return None, "not found"

    async def _try_remembered_strategy(self, intent_data, strategy_type, timeout):
        """Attempt to use a previously successful strategy."""
        try:
            if strategy_type == "primary_selector":
                return await self.page.wait_for_selector(intent_data['primary_selector'], timeout=timeout)
            
            elif strategy_type.startswith("fallback:"):
                method = strategy_type.replace("fallback: ", "")
                # Find the fallback with this method
                for fallback in intent_data.get("fallbacks", []):
                    if fallback["method"] == method:
                        return await self._try_fallback_method(method, fallback["value"], timeout)
        except:
            print(f"⚠️ Remembered strategy '{strategy_type}' failed, continuing with standard flow")
        return None

    async def _try_fallback_method(self, method, value, timeout):
        """Execute a specific fallback method."""
        if method == "aria-label":
            selector = f"[aria-label='{value}']"
            return await self.page.wait_for_selector(selector, timeout=timeout)
        elif method == "xpath":
            selector = f"xpath={value}"
            return await self.page.wait_for_selector(selector, timeout=timeout)
        elif method == "text-contains":
            selector = f"text={value}"
            return await self.page.wait_for_selector(selector, timeout=timeout)
        return None