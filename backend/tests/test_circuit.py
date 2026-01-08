"""
Circuit Breaker Tests
Test circuit breaker state transitions and fallback logic
"""

import pytest
import asyncio
from app.engine.circuit import CircuitBreaker, CircuitBreakerOpen

class TestCircuitBreaker:
    """Test suite for circuit breaker pattern"""
    
    def setup_method(self):
        """Initialize circuit breaker before each test"""
        self.circuit = CircuitBreaker(
            failure_threshold=5,
            timeout_seconds=60,
            half_open_attempts=3
        )
    
    @pytest.mark.asyncio
    async def test_initial_state_closed(self):
        """Test that circuit starts in CLOSED state"""
        assert self.circuit.state == "CLOSED"
        assert self.circuit.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_successful_call_in_closed_state(self):
        """Test successful function execution in CLOSED state"""
        async def success_func():
            return "success"
        
        result = await self.circuit.call(success_func)
        
        assert result == "success"
        assert self.circuit.state == "CLOSED"
        assert self.circuit.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_failure_increments_counter(self):
        """Test that failures increment failure counter"""
        async def failing_func():
            raise Exception("Test failure")
        
        for i in range(3):
            with pytest.raises(Exception):
                await self.circuit.call(failing_func)
        
        assert self.circuit.failure_count == 3
        assert self.circuit.state == "CLOSED"  # Still closed, below threshold
    
    @pytest.mark.asyncio
    async def test_transition_to_open_after_threshold(self):
        """Test CLOSED -> OPEN transition after failure threshold"""
        async def failing_func():
            raise Exception("Test failure")
        
        # Trigger 5 failures to reach threshold
        for i in range(5):
            with pytest.raises(Exception):
                await self.circuit.call(failing_func)
        
        assert self.circuit.state == "OPEN"
        assert self.circuit.failure_count >= 5
    
    @pytest.mark.asyncio
    async def test_open_state_blocks_calls(self):
        """Test that OPEN state immediately rejects calls"""
        # Force circuit to OPEN state
        self.circuit.state = "OPEN"
        self.circuit.last_failure_time = asyncio.get_event_loop().time()
        
        async def any_func():
            return "should not execute"
        
        with pytest.raises(CircuitBreakerOpen):
            await self.circuit.call(any_func)
    
    @pytest.mark.asyncio
    async def test_transition_to_half_open_after_timeout(self):
        """Test OPEN -> HALF_OPEN transition after timeout"""
        # Set circuit to OPEN state with old timestamp
        self.circuit.state = "OPEN"
        self.circuit.last_failure_time = asyncio.get_event_loop().time() - 61  # 61 seconds ago
        
        async def success_func():
            return "success"
        
        result = await self.circuit.call(success_func)
        
        assert result == "success"
        assert self.circuit.state == "HALF_OPEN"
    
    @pytest.mark.asyncio
    async def test_half_open_success_increments_counter(self):
        """Test that successes in HALF_OPEN increment success counter"""
        self.circuit.state = "HALF_OPEN"
        self.circuit.half_open_successes = 0
        
        async def success_func():
            return "success"
        
        await self.circuit.call(success_func)
        
        assert self.circuit.half_open_successes == 1
        assert self.circuit.state == "HALF_OPEN"
    
    @pytest.mark.asyncio
    async def test_transition_to_closed_after_half_open_successes(self):
        """Test HALF_OPEN -> CLOSED after required successes"""
        self.circuit.state = "HALF_OPEN"
        self.circuit.half_open_successes = 0
        
        async def success_func():
            return "success"
        
        # Execute 3 successful calls
        for i in range(3):
            await self.circuit.call(success_func)
        
        assert self.circuit.state == "CLOSED"
        assert self.circuit.failure_count == 0
        assert self.circuit.half_open_successes == 0  # Reset
    
    @pytest.mark.asyncio
    async def test_half_open_failure_returns_to_open(self):
        """Test HALF_OPEN -> OPEN on any failure"""
        self.circuit.state = "HALF_OPEN"
        self.circuit.half_open_successes = 2  # Close to recovery
        
        async def failing_func():
            raise Exception("Test failure")
        
        with pytest.raises(Exception):
            await self.circuit.call(failing_func)
        
        assert self.circuit.state == "OPEN"
        assert self.circuit.half_open_successes == 0
    
    @pytest.mark.asyncio
    async def test_reset_method(self):
        """Test manual circuit breaker reset"""
        # Put circuit in OPEN state
        self.circuit.state = "OPEN"
        self.circuit.failure_count = 10
        
        self.circuit.reset()
        
        assert self.circuit.state == "CLOSED"
        assert self.circuit.failure_count == 0
        assert self.circuit.half_open_successes == 0
    
    @pytest.mark.asyncio
    async def test_get_state_method(self):
        """Test state retrieval with metrics"""
        self.circuit.failure_count = 3
        
        state_info = self.circuit.get_state()
        
        assert state_info['state'] == "CLOSED"
        assert state_info['failure_count'] == 3
        assert 'last_failure_time' in state_info
    
    @pytest.mark.asyncio
    async def test_concurrent_calls_in_closed_state(self):
        """Test handling of concurrent calls"""
        async def slow_success_func():
            await asyncio.sleep(0.1)
            return "success"
        
        # Execute multiple concurrent calls
        tasks = [self.circuit.call(slow_success_func) for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        assert all(r == "success" for r in results)
        assert self.circuit.state == "CLOSED"
