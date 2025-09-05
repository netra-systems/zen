# Team 4: Corpus Admin Consolidation Prompt

## COPY THIS ENTIRE PROMPT:

You are a Corpus Management Expert implementing SSOT consolidation for the Corpus Admin module.

🚨 ULTRA CRITICAL FIRST ACTION - READ RECENT ISSUES:
Before ANY work, you MUST read and internalize the "Recent issues to be extra aware of" section from CLAUDE.md:
1. Race conditions in async/websockets - Plan ahead for concurrency
2. Solve 95% of cases first - Make breadth ironclad before edge cases  
3. Limit volume of code - Delete ugly tests rather than add complex code
4. This is a multi-user system - Always consider concurrent users

MANDATORY READING BEFORE STARTING:
1. CLAUDE.md (entire document, especially sections 2.1, 3.6, 6 AND the recent issues section)
2. USER_CONTEXT_ARCHITECTURE.md (factory patterns)
3. MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
4. SPEC/learnings/ssot_consolidation_20250825.xml
5. Corpus Admin section in DEFINITION_OF_DONE_CHECKLIST.md
6. METADATA_STORAGE_MIGRATION_AUDIT.md (metadata patterns)

YOUR SPECIFIC CONSOLIDATION TASKS:
1. Consolidate 20 files in corpus_admin/ into ONE UnifiedCorpusAdmin
2. Implement factory pattern for multi-user corpus isolation
3. Preserve corpus management functionality
4. Ensure thread-safe corpus operations
5. Migrate metadata operations to BaseAgent SSOT methods

TARGET IMPLEMENTATION:
```python
# Location: netra_backend/app/admin/corpus/unified_corpus_admin.py
class UnifiedCorpusAdminFactory:
    """Factory for creating isolated corpus admin instances"""
    def create_for_context(self, user_context: UserExecutionContext):
        return UnifiedCorpusAdmin(
            context=user_context,
            isolation_strategy=IsolationStrategy.PER_USER_CORPUS
        )

class UnifiedCorpusAdmin:
    """SSOT for ALL corpus management operations"""
    def __init__(self, context: UserExecutionContext):
        self.context = context
        self.user_corpus_path = self._get_user_corpus_path(context.user_id)
        self._lock = asyncio.Lock()  # Thread-safe operations
    
    async def add_to_corpus(self, document: Document, context: UserExecutionContext):
        async with self._lock:
            # Thread-safe corpus modification
            corpus_id = await self._add_document(document)
            # Use SSOT metadata methods
            self.store_metadata_result(context, 'corpus_id', corpus_id)
            self.append_metadata_list(context, 'corpus_operations', 'add')
            return corpus_id
    
    async def search_corpus(self, query: str, context: UserExecutionContext):
        # Read operations can be parallel
        results = await self._search_internal(query)
        self.store_metadata_result(context, 'search_results', results)
        return results
```

FILES TO CONSOLIDATE:
- All 20 files in corpus_admin/
- Corpus indexing utilities
- Corpus search implementations
- Corpus maintenance tools
- Document processing pipelines

CRITICAL REQUIREMENTS:
1. Generate MRO report before refactoring (CLAUDE.md 3.6)
2. Preserve factory patterns for user corpus isolation
3. Maintain thread-safe corpus modifications
4. Support concurrent read operations
5. Validate all named values against MISSION_CRITICAL index
6. Use UnifiedDockerManager for Docker operations
7. Test with real services (mocks forbidden)
8. Extract ALL value from files before deletion
9. Migrate metadata to SSOT methods
10. Ensure multi-user corpus isolation

VALUE PRESERVATION PROCESS (Per File):
1. Run git log - identify corpus management fixes
2. Grep for indexing algorithms
3. Check for search optimizations
4. Extract document processing logic
5. Document in extraction_report_[filename].md
6. Migrate corpus tests
7. ONLY delete after extraction

METADATA MIGRATION (CRITICAL):
Replace direct assignments in corpus operations:
```python
# WRONG:
context.metadata['corpus_size'] = size
context.metadata['indexed_docs'].append(doc_id)

# RIGHT:
self.store_metadata_result(context, 'corpus_size', size)
self.append_metadata_list(context, 'indexed_docs', doc_id)
```

TESTING AT EVERY STAGE:

Stage 1 - Pre-consolidation:
- [ ] Run python tests/unified_test_runner.py --real-services --category corpus
- [ ] Document current corpus structure
- [ ] Create tests for corpus operations
- [ ] Test multi-user corpus isolation
- [ ] Benchmark current search performance

Stage 2 - During consolidation:
- [ ] Test after each file migration
- [ ] Verify corpus isolation per user
- [ ] Test concurrent corpus operations
- [ ] Ensure thread-safety for writes
- [ ] Verify search functionality

Stage 3 - Post-consolidation:
- [ ] Full regression testing
- [ ] Performance benchmarks (search speed)
- [ ] Load test with 10+ users managing corpuses
- [ ] Concurrent modification tests
- [ ] Memory usage for large corpuses

CONTINUOUS BREAKING-CHANGE AUDIT:
After EVERY consolidation step, audit and update:
- [ ] Import statements for corpus_admin/
- [ ] Admin panel corpus management UI
- [ ] API endpoints for corpus operations
- [ ] Background corpus maintenance jobs
- [ ] Corpus indexing pipelines
- [ ] Search API integrations
- [ ] Document upload handlers
- [ ] Corpus statistics collectors
- [ ] Backup/restore procedures
- [ ] Frontend corpus browser

DETAILED REPORTING REQUIREMENTS:
Create reports/team_04_corpus_admin_[timestamp].md with:

## Consolidation Report - Team 4: Corpus Admin
### Phase 1: Analysis
- Files analyzed: 20 in corpus_admin/
- Critical functions: [indexing, search, maintenance]
- Isolation issues: [multi-user concerns]
- Recent fixes: [corpus-related commits]
- Performance bottlenecks: [identified]

### Phase 2: Implementation  
- SSOT location: netra_backend/app/admin/corpus/unified_corpus_admin.py
- Factory pattern: Per-user corpus isolation
- Thread-safety: AsyncIO locks for writes
- Search optimization: [approach used]
- Indexing strategy: [consolidated method]

### Phase 3: Validation
- Tests created: [corpus operation tests]
- Tests passing: [percentage]
- Search performance: [before/after benchmarks]
- Concurrent users: [10 users tested]
- Isolation verified: [user corpuses separate]

### Phase 4: Cleanup
- Files deleted: 20 from corpus_admin/
- Imports updated: [count]
- Documentation: Corpus architecture updated
- Learnings: Multi-user patterns documented

### Evidence of Correctness:
- Test results for corpus operations
- Multi-user isolation proof
- Performance benchmarks (search times)
- Thread-safety verification logs
- Memory usage for 10,000 documents
- Concurrent modification handling

VALIDATION CHECKLIST:
- [ ] MRO report for corpus hierarchy
- [ ] Factory pattern implemented
- [ ] User corpus isolation verified
- [ ] Thread-safe modifications
- [ ] Concurrent reads working
- [ ] Absolute imports used
- [ ] Named values validated
- [ ] Tests with --real-services
- [ ] Value extracted from 20 files
- [ ] Extraction reports complete
- [ ] Metadata using SSOT methods
- [ ] Zero direct assignments
- [ ] Legacy files deleted
- [ ] CLAUDE.md compliance
- [ ] Breaking changes fixed
- [ ] No performance regression
- [ ] Multi-user verified
- [ ] Documentation complete

SUCCESS CRITERIA:
- Single UnifiedCorpusAdmin implementation
- Per-user corpus isolation working
- Thread-safe corpus modifications
- Zero corpus functionality loss
- Search performance maintained/improved
- Indexing operations preserved
- Multi-user corpus management working
- Factory pattern correctly implemented
- All corpus operations consolidated
- Complete audit trail

PRIORITY: P1 HIGH
TIME ALLOCATION: 22 hours
EXPECTED REDUCTION: 20 files → 1 unified implementation