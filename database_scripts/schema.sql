
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
	picture VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	is_active BOOLEAN, 
	is_superuser BOOLEAN, 
	PRIMARY KEY (id)
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
	created_by_id VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by_id) REFERENCES users (id)
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
