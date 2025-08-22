
CREATE TABLE ai_supply_items (
	id VARCHAR NOT NULL, 
	provider VARCHAR NOT NULL, 
	model_name VARCHAR NOT NULL, 
	model_version VARCHAR, 
	pricing_input NUMERIC(10, 4), 
	pricing_output NUMERIC(10, 4), 
	pricing_currency VARCHAR, 
	context_window INTEGER, 
	max_output_tokens INTEGER, 
	capabilities JSON, 
	availability_status VARCHAR, 
	api_endpoints JSON, 
	performance_metrics JSON, 
	last_updated TIMESTAMP WITH TIME ZONE, 
	research_source VARCHAR, 
	confidence_score FLOAT, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
)

;

CREATE TABLE apex_optimizer_agent_run_reports (
	id VARCHAR NOT NULL, 
	run_id VARCHAR NOT NULL, 
	report VARCHAR NOT NULL, 
	timestamp TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
)

;

CREATE TABLE apex_optimizer_agent_runs (
	id VARCHAR NOT NULL, 
	run_id VARCHAR NOT NULL, 
	step_name VARCHAR NOT NULL, 
	step_input JSON, 
	step_output JSON, 
	run_log VARCHAR, 
	timestamp TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
)

;

CREATE TABLE assistants (
	id VARCHAR NOT NULL, 
	object VARCHAR NOT NULL, 
	created_at INTEGER NOT NULL, 
	name VARCHAR, 
	description VARCHAR, 
	model VARCHAR NOT NULL, 
	instructions VARCHAR, 
	tools JSON NOT NULL, 
	file_ids VARCHAR[] NOT NULL, 
	metadata_ JSON, 
	PRIMARY KEY (id)
)

;

CREATE TABLE mcp_external_servers (
	id VARCHAR NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	url TEXT NOT NULL, 
	transport VARCHAR(20) NOT NULL, 
	auth_type VARCHAR(50), 
	credentials JSON, 
	capabilities JSON, 
	metadata_ JSON, 
	status VARCHAR(20) NOT NULL, 
	last_health_check TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)

;

CREATE TABLE mcp_resource_access (
	id VARCHAR NOT NULL, 
	server_name VARCHAR(255) NOT NULL, 
	resource_uri TEXT NOT NULL, 
	content_hash VARCHAR(64), 
	status VARCHAR(20) NOT NULL, 
	user_id VARCHAR, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE mcp_tool_executions (
	id VARCHAR NOT NULL, 
	server_name VARCHAR(255) NOT NULL, 
	tool_name VARCHAR(255) NOT NULL, 
	arguments JSON NOT NULL, 
	result JSON, 
	status VARCHAR(20) NOT NULL, 
	execution_time_ms INTEGER, 
	error_message TEXT, 
	user_id VARCHAR, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE "references" (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	friendly_name VARCHAR NOT NULL, 
	description VARCHAR, 
	type VARCHAR NOT NULL, 
	value VARCHAR NOT NULL, 
	version VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
)

;

CREATE TABLE research_sessions (
	id VARCHAR NOT NULL, 
	query TEXT NOT NULL, 
	session_id VARCHAR, 
	status VARCHAR, 
	research_plan JSON, 
	questions_answered JSON, 
	raw_results JSON, 
	processed_data JSON, 
	citations JSON, 
	initiated_by VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	error_message TEXT, 
	PRIMARY KEY (id)
)

;

CREATE TABLE supplies (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	description VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
)

;

CREATE TABLE supply_options (
	id SERIAL NOT NULL, 
	provider VARCHAR NOT NULL, 
	family VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	hosting_type VARCHAR, 
	cost_per_million_tokens_usd JSON NOT NULL, 
	quality_score FLOAT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
)

;

CREATE TABLE threads (
	id VARCHAR NOT NULL, 
	object VARCHAR NOT NULL, 
	created_at INTEGER NOT NULL, 
	metadata_ JSON, 
	PRIMARY KEY (id)
)

;

CREATE TABLE users (
	id VARCHAR NOT NULL, 
	email VARCHAR NOT NULL, 
	full_name VARCHAR, 
	hashed_password VARCHAR, 
	picture VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	is_active BOOLEAN, 
	is_superuser BOOLEAN, 
	role VARCHAR, 
	permissions JSON, 
	is_developer BOOLEAN, 
	plan_tier VARCHAR, 
	plan_expires_at TIMESTAMP WITH TIME ZONE, 
	feature_flags JSON, 
	tool_permissions JSON, 
	plan_started_at TIMESTAMP WITH TIME ZONE, 
	auto_renew BOOLEAN, 
	payment_status VARCHAR, 
	trial_period INTEGER, 
	PRIMARY KEY (id)
)

;

CREATE TABLE agent_state_snapshots (
	id VARCHAR NOT NULL, 
	run_id VARCHAR NOT NULL, 
	thread_id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	version VARCHAR NOT NULL, 
	schema_version VARCHAR NOT NULL, 
	checkpoint_type VARCHAR NOT NULL, 
	state_data JSON NOT NULL, 
	serialization_format VARCHAR NOT NULL, 
	compression_type VARCHAR, 
	step_count INTEGER NOT NULL, 
	agent_phase VARCHAR, 
	execution_context JSON, 
	created_at TIMESTAMP WITH TIME ZONE, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	is_recovery_point BOOLEAN, 
	recovery_reason VARCHAR, 
	parent_snapshot_id VARCHAR, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_run_checkpoint_time UNIQUE (run_id, checkpoint_type, created_at), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(parent_snapshot_id) REFERENCES agent_state_snapshots (id)
)

;

CREATE TABLE analyses (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	description VARCHAR, 
	status VARCHAR, 
	created_by_id VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by_id) REFERENCES users (id)
)

;

CREATE TABLE corpora (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	description VARCHAR, 
	table_name VARCHAR, 
	status VARCHAR, 
	domain VARCHAR, 
	metadata_ JSON, 
	created_by_id VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by_id) REFERENCES users (id)
)

;

CREATE TABLE corpus_audit_logs (
	id VARCHAR NOT NULL, 
	timestamp TIMESTAMP WITH TIME ZONE, 
	user_id VARCHAR, 
	action VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	corpus_id VARCHAR, 
	resource_type VARCHAR NOT NULL, 
	resource_id VARCHAR, 
	operation_duration_ms FLOAT, 
	result_data JSON, 
	user_agent VARCHAR, 
	ip_address VARCHAR, 
	request_id VARCHAR, 
	session_id VARCHAR, 
	configuration JSON, 
	performance_metrics JSON, 
	error_details JSON, 
	compliance_flags VARCHAR[], 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE TABLE runs (
	id VARCHAR NOT NULL, 
	object VARCHAR NOT NULL, 
	created_at INTEGER NOT NULL, 
	thread_id VARCHAR NOT NULL, 
	assistant_id VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	required_action JSON, 
	last_error JSON, 
	expires_at INTEGER, 
	started_at INTEGER, 
	cancelled_at INTEGER, 
	failed_at INTEGER, 
	completed_at INTEGER, 
	model VARCHAR, 
	instructions VARCHAR, 
	tools JSON NOT NULL, 
	file_ids VARCHAR[] NOT NULL, 
	metadata_ JSON, 
	PRIMARY KEY (id), 
	FOREIGN KEY(thread_id) REFERENCES threads (id), 
	FOREIGN KEY(assistant_id) REFERENCES assistants (id)
)

;

CREATE TABLE secrets (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	key VARCHAR NOT NULL, 
	encrypted_value VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE TABLE supply_update_logs (
	id VARCHAR NOT NULL, 
	supply_item_id VARCHAR NOT NULL, 
	field_updated VARCHAR NOT NULL, 
	old_value JSON, 
	new_value JSON, 
	research_session_id VARCHAR, 
	update_reason VARCHAR, 
	updated_by VARCHAR NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(supply_item_id) REFERENCES ai_supply_items (id), 
	FOREIGN KEY(research_session_id) REFERENCES research_sessions (id)
)

;

CREATE TABLE tool_usage_logs (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	tool_name VARCHAR NOT NULL, 
	category VARCHAR, 
	execution_time_ms INTEGER, 
	tokens_used INTEGER, 
	cost_cents INTEGER, 
	status VARCHAR NOT NULL, 
	plan_tier VARCHAR NOT NULL, 
	permission_check_result JSON, 
	arguments JSON, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE TABLE agent_recovery_logs (
	id VARCHAR NOT NULL, 
	run_id VARCHAR NOT NULL, 
	thread_id VARCHAR NOT NULL, 
	recovery_type VARCHAR NOT NULL, 
	source_snapshot_id VARCHAR, 
	target_snapshot_id VARCHAR, 
	failure_reason VARCHAR, 
	trigger_event VARCHAR NOT NULL, 
	auto_recovery BOOLEAN, 
	recovery_status VARCHAR NOT NULL, 
	recovered_data JSON, 
	lost_data JSON, 
	data_integrity_score INTEGER, 
	recovery_time_ms INTEGER, 
	data_size_kb INTEGER, 
	initiated_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(source_snapshot_id) REFERENCES agent_state_snapshots (id), 
	FOREIGN KEY(target_snapshot_id) REFERENCES agent_state_snapshots (id)
)

;

CREATE TABLE agent_state_transactions (
	id VARCHAR NOT NULL, 
	snapshot_id VARCHAR NOT NULL, 
	run_id VARCHAR NOT NULL, 
	operation_type VARCHAR NOT NULL, 
	field_changes JSON, 
	previous_values JSON, 
	triggered_by VARCHAR NOT NULL, 
	execution_phase VARCHAR, 
	execution_time_ms INTEGER, 
	memory_usage_mb INTEGER, 
	status VARCHAR NOT NULL, 
	error_message TEXT, 
	started_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(snapshot_id) REFERENCES agent_state_snapshots (id)
)

;

CREATE TABLE analysis_results (
	id VARCHAR NOT NULL, 
	analysis_id VARCHAR, 
	data JSON, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(analysis_id) REFERENCES analyses (id)
)

;

CREATE TABLE messages (
	id VARCHAR NOT NULL, 
	object VARCHAR NOT NULL, 
	created_at INTEGER NOT NULL, 
	thread_id VARCHAR NOT NULL, 
	role VARCHAR NOT NULL, 
	content JSON NOT NULL, 
	assistant_id VARCHAR, 
	run_id VARCHAR, 
	file_ids VARCHAR[] NOT NULL, 
	metadata_ JSON, 
	PRIMARY KEY (id), 
	FOREIGN KEY(thread_id) REFERENCES threads (id), 
	FOREIGN KEY(assistant_id) REFERENCES assistants (id), 
	FOREIGN KEY(run_id) REFERENCES runs (id)
)

;

CREATE TABLE steps (
	id VARCHAR NOT NULL, 
	object VARCHAR NOT NULL, 
	created_at INTEGER NOT NULL, 
	run_id VARCHAR NOT NULL, 
	assistant_id VARCHAR NOT NULL, 
	thread_id VARCHAR NOT NULL, 
	type VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	step_details JSON NOT NULL, 
	last_error JSON, 
	expired_at INTEGER, 
	cancelled_at INTEGER, 
	failed_at INTEGER, 
	completed_at INTEGER, 
	metadata_ JSON, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES runs (id), 
	FOREIGN KEY(assistant_id) REFERENCES assistants (id), 
	FOREIGN KEY(thread_id) REFERENCES threads (id)
)

;
