--
-- PostgreSQL database dump
--

-- Dumped from database version 15.13 (Debian 15.13-1.pgdg120+1)
-- Dumped by pg_dump version 15.13 (Debian 15.13-1.pgdg120+1)

-- Started on 2025-06-19 14:20:13 UTC

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY public.workspaces DROP CONSTRAINT IF EXISTS workspaces_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public.sentences DROP CONSTRAINT IF EXISTS sentences_section_id_fkey;
ALTER TABLE IF EXISTS ONLY public.sentences DROP CONSTRAINT IF EXISTS sentences_paper_id_fkey;
ALTER TABLE IF EXISTS ONLY public.processing_tasks DROP CONSTRAINT IF EXISTS processing_tasks_parent_task_id_fkey;
ALTER TABLE IF EXISTS ONLY public.processing_tasks DROP CONSTRAINT IF EXISTS processing_tasks_paper_id_fkey;
ALTER TABLE IF EXISTS ONLY public.processing_queue DROP CONSTRAINT IF EXISTS processing_queue_paper_id_fkey;
ALTER TABLE IF EXISTS ONLY public.processing_events DROP CONSTRAINT IF EXISTS processing_events_task_id_fkey;
ALTER TABLE IF EXISTS ONLY public.processing_errors DROP CONSTRAINT IF EXISTS processing_errors_task_id_fkey;
ALTER TABLE IF EXISTS ONLY public.paper_selections DROP CONSTRAINT IF EXISTS paper_selections_paper_id_fkey;
ALTER TABLE IF EXISTS ONLY public.paper_sections DROP CONSTRAINT IF EXISTS paper_sections_paper_id_fkey;
ALTER TABLE IF EXISTS ONLY public.chat_histories DROP CONSTRAINT IF EXISTS chat_histories_workspace_id_fkey;
DROP TRIGGER IF EXISTS update_workspaces_updated_at ON public.workspaces;
DROP TRIGGER IF EXISTS update_users_updated_at ON public.users;
DROP TRIGGER IF EXISTS update_system_settings_updated_at ON public.system_settings;
DROP INDEX IF EXISTS public.idx_workspaces_user_id;
DROP INDEX IF EXISTS public.idx_users_google_id;
DROP INDEX IF EXISTS public.idx_users_email;
DROP INDEX IF EXISTS public.idx_sentences_text_search;
DROP INDEX IF EXISTS public.idx_sentences_retry_count;
DROP INDEX IF EXISTS public.idx_sentences_paper_section;
DROP INDEX IF EXISTS public.idx_sentences_has_objective;
DROP INDEX IF EXISTS public.idx_sentences_has_dataset;
DROP INDEX IF EXISTS public.idx_sentences_has_contribution;
DROP INDEX IF EXISTS public.idx_sentences_detection_status;
DROP INDEX IF EXISTS public.idx_selections_paper;
DROP INDEX IF EXISTS public.idx_sections_type;
DROP INDEX IF EXISTS public.idx_sections_paper_id;
DROP INDEX IF EXISTS public.idx_queue_status_priority;
DROP INDEX IF EXISTS public.idx_queue_paper_stage;
DROP INDEX IF EXISTS public.idx_processing_tasks_task_id;
DROP INDEX IF EXISTS public.idx_processing_tasks_status;
DROP INDEX IF EXISTS public.idx_processing_tasks_parent;
DROP INDEX IF EXISTS public.idx_processing_tasks_paper_id;
DROP INDEX IF EXISTS public.idx_processing_tasks_created_at;
DROP INDEX IF EXISTS public.idx_processing_events_type;
DROP INDEX IF EXISTS public.idx_processing_events_task_id;
DROP INDEX IF EXISTS public.idx_processing_events_created_at;
DROP INDEX IF EXISTS public.idx_processing_errors_type;
DROP INDEX IF EXISTS public.idx_processing_errors_task_id;
DROP INDEX IF EXISTS public.idx_processing_errors_severity;
DROP INDEX IF EXISTS public.idx_processing_errors_created_at;
DROP INDEX IF EXISTS public.idx_papers_status;
DROP INDEX IF EXISTS public.idx_papers_hash;
DROP INDEX IF EXISTS public.idx_papers_created_at;
DROP INDEX IF EXISTS public.idx_chat_histories_workspace_id;
DROP INDEX IF EXISTS public.idx_chat_histories_created_at;
ALTER TABLE IF EXISTS ONLY public.workspaces DROP CONSTRAINT IF EXISTS workspaces_pkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_pkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_google_id_key;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_email_key;
ALTER TABLE IF EXISTS ONLY public.system_settings DROP CONSTRAINT IF EXISTS system_settings_setting_key_key;
ALTER TABLE IF EXISTS ONLY public.system_settings DROP CONSTRAINT IF EXISTS system_settings_pkey;
ALTER TABLE IF EXISTS ONLY public.sentences DROP CONSTRAINT IF EXISTS sentences_pkey;
ALTER TABLE IF EXISTS ONLY public.processing_tasks DROP CONSTRAINT IF EXISTS processing_tasks_task_id_key;
ALTER TABLE IF EXISTS ONLY public.processing_tasks DROP CONSTRAINT IF EXISTS processing_tasks_pkey;
ALTER TABLE IF EXISTS ONLY public.processing_queue DROP CONSTRAINT IF EXISTS processing_queue_pkey;
ALTER TABLE IF EXISTS ONLY public.processing_events DROP CONSTRAINT IF EXISTS processing_events_pkey;
ALTER TABLE IF EXISTS ONLY public.processing_errors DROP CONSTRAINT IF EXISTS processing_errors_pkey;
ALTER TABLE IF EXISTS ONLY public.papers DROP CONSTRAINT IF EXISTS papers_pkey;
ALTER TABLE IF EXISTS ONLY public.papers DROP CONSTRAINT IF EXISTS papers_file_hash_key;
ALTER TABLE IF EXISTS ONLY public.paper_selections DROP CONSTRAINT IF EXISTS paper_selections_pkey;
ALTER TABLE IF EXISTS ONLY public.paper_selections DROP CONSTRAINT IF EXISTS paper_selections_paper_id_key;
ALTER TABLE IF EXISTS ONLY public.paper_sections DROP CONSTRAINT IF EXISTS paper_sections_pkey;
ALTER TABLE IF EXISTS ONLY public.chat_histories DROP CONSTRAINT IF EXISTS chat_histories_pkey;
ALTER TABLE IF EXISTS ONLY public.alembic_version DROP CONSTRAINT IF EXISTS alembic_version_pkc;
DROP TABLE IF EXISTS public.workspaces;
DROP TABLE IF EXISTS public.users;
DROP TABLE IF EXISTS public.system_settings;
DROP TABLE IF EXISTS public.sentences;
DROP TABLE IF EXISTS public.processing_tasks;
DROP TABLE IF EXISTS public.processing_queue;
DROP TABLE IF EXISTS public.processing_events;
DROP TABLE IF EXISTS public.processing_errors;
DROP TABLE IF EXISTS public.papers;
DROP TABLE IF EXISTS public.paper_selections;
DROP TABLE IF EXISTS public.paper_sections;
DROP TABLE IF EXISTS public.chat_histories;
DROP TABLE IF EXISTS public.alembic_version;
DROP FUNCTION IF EXISTS public.update_updated_at_column();
DROP EXTENSION IF EXISTS "uuid-ossp";
--
-- TOC entry 2 (class 3079 OID 16385)
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- TOC entry 3537 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- TOC entry 238 (class 1255 OID 16576)
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 224 (class 1259 OID 16597)
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- TOC entry 227 (class 1259 OID 16632)
-- Name: chat_histories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_histories (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    workspace_id uuid NOT NULL,
    role character varying(20) NOT NULL,
    content text NOT NULL,
    message_metadata jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chat_histories_role_check CHECK (((role)::text = ANY ((ARRAY['user'::character varying, 'assistant'::character varying])::text[])))
);


--
-- TOC entry 216 (class 1259 OID 16413)
-- Name: paper_sections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.paper_sections (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    paper_id uuid,
    section_type character varying(50) NOT NULL,
    page_num integer,
    content text NOT NULL,
    section_order integer,
    tei_coordinates jsonb,
    word_count integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 218 (class 1259 OID 16449)
-- Name: paper_selections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.paper_selections (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    paper_id uuid,
    is_selected boolean DEFAULT true,
    selected_timestamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 215 (class 1259 OID 16396)
-- Name: papers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.papers (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    file_name character varying(255) NOT NULL,
    original_filename character varying(255),
    upload_timestamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    processing_status character varying(50) DEFAULT 'uploading'::character varying,
    file_size bigint,
    file_hash character varying(64),
    grobid_processed boolean DEFAULT false,
    sentences_processed boolean DEFAULT false,
    od_cd_processed boolean DEFAULT false,
    pdf_deleted boolean DEFAULT false,
    error_message text,
    tei_xml text,
    tei_metadata jsonb,
    processing_completed_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 223 (class 1259 OID 16533)
-- Name: processing_errors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.processing_errors (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    task_id uuid,
    error_type character varying(50) NOT NULL,
    error_code character varying(20),
    error_message text NOT NULL,
    stack_trace text,
    context_data jsonb,
    severity character varying(20) DEFAULT 'error'::character varying,
    is_recoverable boolean DEFAULT false,
    recovery_suggestion text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 222 (class 1259 OID 16519)
-- Name: processing_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.processing_events (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    task_id uuid,
    event_type character varying(50) NOT NULL,
    event_name character varying(100),
    message text,
    step_number integer,
    total_steps integer,
    percentage numeric(5,2),
    details jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 219 (class 1259 OID 16464)
-- Name: processing_queue; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.processing_queue (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    paper_id uuid,
    processing_stage character varying(50) NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    priority integer DEFAULT 0,
    retry_count integer DEFAULT 0,
    max_retries integer DEFAULT 3,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    error_message text,
    processing_details jsonb
);


--
-- TOC entry 221 (class 1259 OID 16493)
-- Name: processing_tasks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.processing_tasks (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    paper_id uuid,
    task_id character varying(64) NOT NULL,
    task_type character varying(50) NOT NULL,
    priority smallint DEFAULT 2,
    retries smallint DEFAULT 0,
    max_retries smallint DEFAULT 3,
    status character varying(32) DEFAULT 'pending'::character varying NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    timeout_seconds integer DEFAULT 1800,
    data jsonb,
    result jsonb,
    error_message text,
    user_id character varying(50),
    parent_task_id uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 217 (class 1259 OID 16427)
-- Name: sentences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sentences (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    paper_id uuid,
    section_id uuid,
    content text NOT NULL,
    sentence_order integer,
    word_count integer,
    char_count integer,
    has_objective boolean,
    has_dataset boolean,
    has_contribution boolean,
    detection_status character varying(20) DEFAULT 'unknown'::character varying,
    error_message text,
    retry_count integer DEFAULT 0,
    explanation text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 220 (class 1259 OID 16482)
-- Name: system_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_settings (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    setting_key character varying(100) NOT NULL,
    setting_value jsonb,
    description text,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 225 (class 1259 OID 16605)
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    google_id character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    picture_url character varying(500),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 226 (class 1259 OID 16619)
-- Name: workspaces; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workspaces (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- TOC entry 3360 (class 2606 OID 16601)
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- TOC entry 3373 (class 2606 OID 16641)
-- Name: chat_histories chat_histories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_histories
    ADD CONSTRAINT chat_histories_pkey PRIMARY KEY (id);


--
-- TOC entry 3316 (class 2606 OID 16421)
-- Name: paper_sections paper_sections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_sections
    ADD CONSTRAINT paper_sections_pkey PRIMARY KEY (id);


--
-- TOC entry 3328 (class 2606 OID 16458)
-- Name: paper_selections paper_selections_paper_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_selections
    ADD CONSTRAINT paper_selections_paper_id_key UNIQUE (paper_id);


--
-- TOC entry 3330 (class 2606 OID 16456)
-- Name: paper_selections paper_selections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_selections
    ADD CONSTRAINT paper_selections_pkey PRIMARY KEY (id);


--
-- TOC entry 3310 (class 2606 OID 16412)
-- Name: papers papers_file_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.papers
    ADD CONSTRAINT papers_file_hash_key UNIQUE (file_hash);


--
-- TOC entry 3312 (class 2606 OID 16410)
-- Name: papers papers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.papers
    ADD CONSTRAINT papers_pkey PRIMARY KEY (id);


--
-- TOC entry 3358 (class 2606 OID 16543)
-- Name: processing_errors processing_errors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processing_errors
    ADD CONSTRAINT processing_errors_pkey PRIMARY KEY (id);


--
-- TOC entry 3352 (class 2606 OID 16527)
-- Name: processing_events processing_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processing_events
    ADD CONSTRAINT processing_events_pkey PRIMARY KEY (id);


--
-- TOC entry 3334 (class 2606 OID 16476)
-- Name: processing_queue processing_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processing_queue
    ADD CONSTRAINT processing_queue_pkey PRIMARY KEY (id);


--
-- TOC entry 3345 (class 2606 OID 16506)
-- Name: processing_tasks processing_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processing_tasks
    ADD CONSTRAINT processing_tasks_pkey PRIMARY KEY (id);


--
-- TOC entry 3347 (class 2606 OID 16508)
-- Name: processing_tasks processing_tasks_task_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processing_tasks
    ADD CONSTRAINT processing_tasks_task_id_key UNIQUE (task_id);


--
-- TOC entry 3325 (class 2606 OID 16438)
-- Name: sentences sentences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sentences
    ADD CONSTRAINT sentences_pkey PRIMARY KEY (id);


--
-- TOC entry 3336 (class 2606 OID 16490)
-- Name: system_settings system_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_settings
    ADD CONSTRAINT system_settings_pkey PRIMARY KEY (id);


--
-- TOC entry 3338 (class 2606 OID 16492)
-- Name: system_settings system_settings_setting_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_settings
    ADD CONSTRAINT system_settings_setting_key_key UNIQUE (setting_key);


--
-- TOC entry 3364 (class 2606 OID 16618)
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- TOC entry 3366 (class 2606 OID 16616)
-- Name: users users_google_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_google_id_key UNIQUE (google_id);


--
-- TOC entry 3368 (class 2606 OID 16614)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 3371 (class 2606 OID 16626)
-- Name: workspaces workspaces_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspaces
    ADD CONSTRAINT workspaces_pkey PRIMARY KEY (id);


--
-- TOC entry 3374 (class 1259 OID 16651)
-- Name: idx_chat_histories_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_chat_histories_created_at ON public.chat_histories USING btree (created_at);


--
-- TOC entry 3375 (class 1259 OID 16650)
-- Name: idx_chat_histories_workspace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_chat_histories_workspace_id ON public.chat_histories USING btree (workspace_id);


--
-- TOC entry 3306 (class 1259 OID 16551)
-- Name: idx_papers_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_papers_created_at ON public.papers USING btree (created_at);


--
-- TOC entry 3307 (class 1259 OID 16549)
-- Name: idx_papers_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_papers_hash ON public.papers USING btree (file_hash);


--
-- TOC entry 3308 (class 1259 OID 16550)
-- Name: idx_papers_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_papers_status ON public.papers USING btree (processing_status);


--
-- TOC entry 3353 (class 1259 OID 16574)
-- Name: idx_processing_errors_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_processing_errors_created_at ON public.processing_errors USING btree (created_at);


--
-- TOC entry 3354 (class 1259 OID 16575)
-- Name: idx_processing_errors_severity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_processing_errors_severity ON public.processing_errors USING btree (severity);


--
-- TOC entry 3355 (class 1259 OID 16572)
-- Name: idx_processing_errors_task_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_processing_errors_task_id ON public.processing_errors USING btree (task_id);


--
-- TOC entry 3356 (class 1259 OID 16573)
-- Name: idx_processing_errors_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_processing_errors_type ON public.processing_errors USING btree (error_type);


--
-- TOC entry 3348 (class 1259 OID 16571)
-- Name: idx_processing_events_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_processing_events_created_at ON public.processing_events USING btree (created_at);


--
-- TOC entry 3349 (class 1259 OID 16569)
-- Name: idx_processing_events_task_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_processing_events_task_id ON public.processing_events USING btree (task_id);


--
-- TOC entry 3350 (class 1259 OID 16570)
-- Name: idx_processing_events_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_processing_events_type ON public.processing_events USING btree (event_type);


--
-- TOC entry 3339 (class 1259 OID 16567)
-- Name: idx_processing_tasks_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_processing_tasks_created_at ON public.processing_tasks USING btree (created_at);


--
-- TOC entry 3340 (class 1259 OID 16564)
-- Name: idx_processing_tasks_paper_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_processing_tasks_paper_id ON public.processing_tasks USING btree (paper_id);


--
-- TOC entry 3341 (class 1259 OID 16568)
-- Name: idx_processing_tasks_parent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_processing_tasks_parent ON public.processing_tasks USING btree (parent_task_id);


--
-- TOC entry 3342 (class 1259 OID 16566)
-- Name: idx_processing_tasks_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_processing_tasks_status ON public.processing_tasks USING btree (status);


--
-- TOC entry 3343 (class 1259 OID 16565)
-- Name: idx_processing_tasks_task_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_processing_tasks_task_id ON public.processing_tasks USING btree (task_id);


--
-- TOC entry 3331 (class 1259 OID 16562)
-- Name: idx_queue_paper_stage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_queue_paper_stage ON public.processing_queue USING btree (paper_id, processing_stage);


--
-- TOC entry 3332 (class 1259 OID 16561)
-- Name: idx_queue_status_priority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_queue_status_priority ON public.processing_queue USING btree (status, priority);


--
-- TOC entry 3313 (class 1259 OID 16552)
-- Name: idx_sections_paper_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sections_paper_id ON public.paper_sections USING btree (paper_id);


--
-- TOC entry 3314 (class 1259 OID 16553)
-- Name: idx_sections_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sections_type ON public.paper_sections USING btree (section_type);


--
-- TOC entry 3326 (class 1259 OID 16563)
-- Name: idx_selections_paper; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_selections_paper ON public.paper_selections USING btree (paper_id);


--
-- TOC entry 3317 (class 1259 OID 16554)
-- Name: idx_sentences_detection_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sentences_detection_status ON public.sentences USING btree (detection_status);


--
-- TOC entry 3318 (class 1259 OID 16560)
-- Name: idx_sentences_has_contribution; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sentences_has_contribution ON public.sentences USING btree (has_contribution);


--
-- TOC entry 3319 (class 1259 OID 16559)
-- Name: idx_sentences_has_dataset; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sentences_has_dataset ON public.sentences USING btree (has_dataset);


--
-- TOC entry 3320 (class 1259 OID 16558)
-- Name: idx_sentences_has_objective; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sentences_has_objective ON public.sentences USING btree (has_objective);


--
-- TOC entry 3321 (class 1259 OID 16555)
-- Name: idx_sentences_paper_section; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sentences_paper_section ON public.sentences USING btree (paper_id, section_id);


--
-- TOC entry 3322 (class 1259 OID 16557)
-- Name: idx_sentences_retry_count; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sentences_retry_count ON public.sentences USING btree (retry_count);


--
-- TOC entry 3323 (class 1259 OID 16556)
-- Name: idx_sentences_text_search; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sentences_text_search ON public.sentences USING gin (to_tsvector('english'::regconfig, content));


--
-- TOC entry 3361 (class 1259 OID 16648)
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- TOC entry 3362 (class 1259 OID 16647)
-- Name: idx_users_google_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_google_id ON public.users USING btree (google_id);


--
-- TOC entry 3369 (class 1259 OID 16649)
-- Name: idx_workspaces_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_workspaces_user_id ON public.workspaces USING btree (user_id);


--
-- TOC entry 3387 (class 2620 OID 16577)
-- Name: system_settings update_system_settings_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_system_settings_updated_at BEFORE UPDATE ON public.system_settings FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 3388 (class 2620 OID 16652)
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 3389 (class 2620 OID 16653)
-- Name: workspaces update_workspaces_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_workspaces_updated_at BEFORE UPDATE ON public.workspaces FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 3386 (class 2606 OID 16642)
-- Name: chat_histories chat_histories_workspace_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_histories
    ADD CONSTRAINT chat_histories_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES public.workspaces(id) ON DELETE CASCADE;


--
-- TOC entry 3376 (class 2606 OID 16422)
-- Name: paper_sections paper_sections_paper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_sections
    ADD CONSTRAINT paper_sections_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.papers(id) ON DELETE CASCADE;


--
-- TOC entry 3379 (class 2606 OID 16459)
-- Name: paper_selections paper_selections_paper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.paper_selections
    ADD CONSTRAINT paper_selections_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.papers(id) ON DELETE CASCADE;


--
-- TOC entry 3384 (class 2606 OID 16544)
-- Name: processing_errors processing_errors_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processing_errors
    ADD CONSTRAINT processing_errors_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.processing_tasks(id) ON DELETE CASCADE;


--
-- TOC entry 3383 (class 2606 OID 16528)
-- Name: processing_events processing_events_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processing_events
    ADD CONSTRAINT processing_events_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.processing_tasks(id) ON DELETE CASCADE;


--
-- TOC entry 3380 (class 2606 OID 16477)
-- Name: processing_queue processing_queue_paper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processing_queue
    ADD CONSTRAINT processing_queue_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.papers(id) ON DELETE CASCADE;


--
-- TOC entry 3381 (class 2606 OID 16509)
-- Name: processing_tasks processing_tasks_paper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processing_tasks
    ADD CONSTRAINT processing_tasks_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.papers(id) ON DELETE CASCADE;


--
-- TOC entry 3382 (class 2606 OID 16514)
-- Name: processing_tasks processing_tasks_parent_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processing_tasks
    ADD CONSTRAINT processing_tasks_parent_task_id_fkey FOREIGN KEY (parent_task_id) REFERENCES public.processing_tasks(id);


--
-- TOC entry 3377 (class 2606 OID 16439)
-- Name: sentences sentences_paper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sentences
    ADD CONSTRAINT sentences_paper_id_fkey FOREIGN KEY (paper_id) REFERENCES public.papers(id) ON DELETE CASCADE;


--
-- TOC entry 3378 (class 2606 OID 16444)
-- Name: sentences sentences_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sentences
    ADD CONSTRAINT sentences_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.paper_sections(id) ON DELETE CASCADE;


--
-- TOC entry 3385 (class 2606 OID 16627)
-- Name: workspaces workspaces_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspaces
    ADD CONSTRAINT workspaces_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Completed on 2025-06-19 14:20:13 UTC

--
-- PostgreSQL database dump complete
--

