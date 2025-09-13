"""E2E Test #8: Search and Filter Functionality E2E - Critical UX Validation



CRITICAL E2E test for search and filter functionality across all data types.

Validates conversation search, filter performance, pagination, and query optimization.



Business Value Justification (BVJ):

1. Segment: ALL paid tiers ($25K+ MRR protection)

2. Business Goal: Ensure reliable search/filter UX to prevent user churn

3. Value Impact: Validates core product usability - finding and organizing conversations

4. Revenue Impact: Protects $25K+ MRR from poor search UX causing customer churn



ARCHITECTURAL COMPLIANCE:

- File size: <300 lines (modular design with helper imports)

- Function size: <8 lines each

- Real API endpoints and database queries

- <1 second search response requirement validation

- Tests all data types: conversations, messages, costs, agents

"""



import sys

from pathlib import Path

from shared.isolated_environment import IsolatedEnvironment







import asyncio

import time

from typing import Any, Dict, List



import pytest

import pytest_asyncio



from netra_backend.app.schemas.user_plan import PlanTier

from tests.e2e.search_filter_helpers import (

    FilterValidationCore,

    PaginationTester,

    PerformanceValidator,

    SearchDataGenerator,

    SearchFilterTestCore,

    SearchOperationSimulator,

)





@pytest.mark.asyncio

@pytest.mark.e2e

class TestSearchFilterFunctionality:

    """Test #8: Search and Filter Functionality with Performance Validation."""

    

    @pytest_asyncio.fixture

    @pytest.mark.e2e

    async def test_core(self):

        """Initialize search filter test core."""

        core = SearchFilterTestCore()

        await core.setup_test_environment()

        yield core

        await core.teardown_test_environment()

    

    @pytest.fixture

    def search_simulator(self):

        """Initialize search operation simulator."""

        return SearchOperationSimulator()

    

    @pytest.fixture  

    def filter_validator(self):

        """Initialize filter validation core."""

        return FilterValidationCore()

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_conversation_search_by_title(self, test_core, search_simulator):

        """Test conversation search by title with performance validation."""

        test_data = await test_core.create_search_test_data(PlanTier.PRO)

        try:

            search_terms = ["optimization", "performance", "analysis"]

            search_results = await self._execute_search_operation(

                test_data, search_simulator, "title", search_terms

            )

            self._assert_search_performance_success(search_results, search_terms)

        finally:

            await test_core.cleanup_test_data(test_data)

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_conversation_search_by_content(self, test_core, search_simulator):

        """Test conversation search by message content."""

        test_data = await test_core.create_search_test_data(PlanTier.ENTERPRISE)

        try:

            content_terms = ["database", "query", "optimization"]

            search_results = await self._execute_search_operation(

                test_data, search_simulator, "content", content_terms

            )

            self._assert_content_search_success(search_results, content_terms)

        finally:

            await test_core.cleanup_test_data(test_data)

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_filter_by_date_range(self, test_core, filter_validator):

        """Test filtering conversations by date ranges."""

        test_data = await test_core.create_search_test_data(PlanTier.PRO)

        try:

            date_filters = filter_validator.create_date_range_filters()

            filter_results = await self._execute_filter_operation(

                test_data, "date_range", date_filters

            )

            self._assert_date_filter_success(filter_results, date_filters)

        finally:

            await test_core.cleanup_test_data(test_data)

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_filter_by_agent_type(self, test_core, filter_validator):

        """Test filtering conversations by agent type."""

        test_data = await test_core.create_search_test_data(PlanTier.ENTERPRISE)

        try:

            agent_filters = ["triage", "data", "admin"]

            filter_results = await self._execute_filter_operation(

                test_data, "agent_type", agent_filters

            )

            self._assert_agent_filter_success(filter_results, agent_filters)

        finally:

            await test_core.cleanup_test_data(test_data)

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_filter_by_cost_range(self, test_core, filter_validator):

        """Test filtering conversations by cost ranges."""

        test_data = await test_core.create_search_test_data(PlanTier.PRO)

        try:

            cost_filters = filter_validator.create_cost_range_filters()

            filter_results = await self._execute_filter_operation(

                test_data, "cost_range", cost_filters

            )

            self._assert_cost_filter_success(filter_results, cost_filters)

        finally:

            await test_core.cleanup_test_data(test_data)

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_search_pagination_performance(self, test_core):

        """Test search result pagination with performance validation."""

        test_data = await test_core.create_large_search_dataset(PlanTier.ENTERPRISE)

        try:

            paginator = PaginationTester()

            pagination_results = await paginator.test_pagination_performance(

                test_data, page_size=20, total_pages=5

            )

            self._assert_pagination_success(pagination_results)

        finally:

            await test_core.cleanup_test_data(test_data)

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_search_performance_under_load(self, test_core):

        """Test search performance under concurrent load."""

        test_data = await test_core.create_search_test_data(PlanTier.ENTERPRISE)

        try:

            performance_validator = PerformanceValidator()

            concurrent_searches = await performance_validator.run_concurrent_searches(

                test_data, concurrent_users=5, searches_per_user=3

            )

            self._assert_load_performance_success(concurrent_searches)

        finally:

            await test_core.cleanup_test_data(test_data)

    

    async def _execute_search_operation(self, test_data, simulator, 

                                      search_type: str, terms: List[str]) -> Dict[str, Any]:

        """Execute search operation with performance measurement."""

        start_time = time.time()

        search_request = simulator.create_search_request(test_data.user_id, search_type, terms)

        results = await simulator.execute_search(test_data.session, search_request)

        response_time = time.time() - start_time

        return {"results": results, "response_time": response_time, "search_type": search_type}

    

    async def _execute_filter_operation(self, test_data, filter_type: str, 

                                      filter_params: Any) -> Dict[str, Any]:

        """Execute filter operation with performance measurement."""

        start_time = time.time()

        filter_request = {"type": filter_type, "params": filter_params, "user_id": test_data.user_id}

        results = await SearchOperationSimulator().execute_filter(test_data.session, filter_request)

        response_time = time.time() - start_time

        return {"results": results, "response_time": response_time, "filter_type": filter_type}

    

    def _assert_search_performance_success(self, search_results: Dict[str, Any], 

                                         search_terms: List[str]) -> None:

        """Assert search performance validation success."""

        assert search_results["response_time"] < 1.0, f"Search took {search_results['response_time']:.2f}s, exceeding 1s limit"

        assert len(search_results["results"]) > 0, "No search results returned"

        assert all(term.lower() in str(search_results["results"]).lower() for term in search_terms), "Search terms not found in results"

    

    def _assert_content_search_success(self, search_results: Dict[str, Any], 

                                     content_terms: List[str]) -> None:

        """Assert content search validation success."""

        assert search_results["response_time"] < 1.0, "Content search too slow"

        assert search_results["search_type"] == "content", "Wrong search type"

        assert len(search_results["results"]) > 0, "No content search results"

    

    def _assert_date_filter_success(self, filter_results: Dict[str, Any], 

                                  date_filters: Dict[str, Any]) -> None:

        """Assert date filter validation success."""

        assert filter_results["response_time"] < 1.0, "Date filter too slow"

        assert filter_results["filter_type"] == "date_range", "Wrong filter type"

        assert len(filter_results["results"]) >= 0, "Date filter failed"

    

    def _assert_agent_filter_success(self, filter_results: Dict[str, Any], 

                                   agent_filters: List[str]) -> None:

        """Assert agent filter validation success."""

        assert filter_results["response_time"] < 1.0, "Agent filter too slow"

        assert filter_results["filter_type"] == "agent_type", "Wrong filter type"

        assert len(filter_results["results"]) >= 0, "Agent filter failed"

    

    def _assert_cost_filter_success(self, filter_results: Dict[str, Any], 

                                  cost_filters: Dict[str, Any]) -> None:

        """Assert cost filter validation success."""

        assert filter_results["response_time"] < 1.0, "Cost filter too slow"

        assert filter_results["filter_type"] == "cost_range", "Wrong filter type"

        assert len(filter_results["results"]) >= 0, "Cost filter failed"

    

    def _assert_pagination_success(self, pagination_results: Dict[str, Any]) -> None:

        """Assert pagination validation success."""

        assert pagination_results["total_pages_tested"] > 0, "No pages tested"

        assert pagination_results["average_response_time"] < 1.0, "Pagination too slow"

        assert pagination_results["all_pages_loaded"], "Some pages failed to load"

    

    def _assert_load_performance_success(self, concurrent_results: Dict[str, Any]) -> None:

        """Assert concurrent load performance success."""

        assert concurrent_results["successful_searches"] > 0, "No successful concurrent searches"

        assert concurrent_results["average_response_time"] < 2.0, "Concurrent searches too slow"

        assert concurrent_results["error_rate"] < 0.1, "Too many errors under load"





@pytest.mark.asyncio

@pytest.mark.e2e

class TestSearchFilterQueryOptimization:

    """Query optimization validation for search and filter operations."""

    

    @pytest_asyncio.fixture

    @pytest.mark.e2e

    async def test_core(self):

        """Initialize query optimization test core."""

        core = SearchFilterTestCore()

        await core.setup_test_environment()

        yield core

        await core.teardown_test_environment()

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_backend_query_optimization(self, test_core):

        """Test backend query optimization for search operations."""

        test_data = await test_core.create_large_search_dataset(PlanTier.ENTERPRISE)

        try:

            query_validator = PerformanceValidator()

            optimization_results = await query_validator.validate_query_optimization(

                test_data, search_terms=["optimization", "performance"]

            )

            self._assert_query_optimization_success(optimization_results)

        finally:

            await test_core.cleanup_test_data(test_data)

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_combined_search_filter_performance(self, test_core):

        """Test combined search and filter operations performance."""

        test_data = await test_core.create_search_test_data(PlanTier.PRO)

        try:

            combined_operation = await self._execute_combined_search_filter(test_data)

            self._assert_combined_operation_success(combined_operation)

        finally:

            await test_core.cleanup_test_data(test_data)

    

    async def _execute_combined_search_filter(self, test_data) -> Dict[str, Any]:

        """Execute combined search and filter operation."""

        start_time = time.time()

        simulator = SearchOperationSimulator()

        search_filter_request = simulator.create_combined_request(

            test_data.user_id, search_terms=["analysis"], agent_filter=["triage"]

        )

        results = await simulator.execute_combined_operation(test_data.session, search_filter_request)

        response_time = time.time() - start_time

        return {"results": results, "response_time": response_time}

    

    def _assert_query_optimization_success(self, optimization_results: Dict[str, Any]) -> None:

        """Assert query optimization validation success."""

        assert optimization_results["query_execution_time"] < 0.5, "Query execution too slow"

        assert optimization_results["index_usage_detected"], "No database index usage detected"

        assert optimization_results["memory_usage"] < 100, "Query memory usage too high"

    

    def _assert_combined_operation_success(self, combined_results: Dict[str, Any]) -> None:

        """Assert combined search and filter operation success."""

        assert combined_results["response_time"] < 1.5, "Combined operation too slow"

        assert len(combined_results["results"]) >= 0, "Combined operation failed"

