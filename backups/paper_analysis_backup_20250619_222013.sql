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
-- TOC entry 3550 (class 0 OID 0)
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
-- TOC entry 3541 (class 0 OID 16597)
-- Dependencies: 224
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.alembic_version (version_num) FROM stdin;
001_users_workspaces_chat
\.


--
-- TOC entry 3544 (class 0 OID 16632)
-- Dependencies: 227
-- Data for Name: chat_histories; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.chat_histories (id, workspace_id, role, content, message_metadata, created_at) FROM stdin;
\.


--
-- TOC entry 3533 (class 0 OID 16413)
-- Dependencies: 216
-- Data for Name: paper_sections; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.paper_sections (id, paper_id, section_type, page_num, content, section_order, tei_coordinates, word_count, created_at) FROM stdin;
512941ed-3c18-462b-98a6-07f8d02f9054	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	other	3	In the articles the dependent variable was defined as adaptive expert or adaptive expertise (5), adaptive performance (15), and adaptive transfer (1). Two articles were published before 2000, 12 before 2010, and 7 after 2010. Quantitative studies were conducted 14 times and seven studies used a mixed-method approach. Ten studies were conducted at the workplace, six in an educational context, and five were simulation studies. Workplace studies were conducted in several industries (hospitality = 2; military = 1; aerospace = 1; electric power utility company = 1, and government agency = 1) and also across industries (4). The studies conducted in educational contexts dealt with experienced firefighters (2) and engineering pupils/students (4). Table Adaptive expertise has been measured through different methods. These methods are summarized in Table	4	\N	127	2025-06-14 12:09:51.6095
0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	introduction	2	Today's work environments are characterized by increasing complexity due to higher levels of required knowledge and task volatility Adaptive expertise is generally seen as important, but its characteristics and development are ill understood. Achieving a better understanding of the concept of adaptive expertise is necessary to design learning activities that contribute to its development. Therefore, the aim of this systematic review is to establish what the characteristics of adaptive expertise are and with which training and task characteristics it flourishes. By analyzing the characteristics that distinguish adaptive expertise from routine expertise, it will become possible to deduct what learning activities lead to it. Hatano and Inagaki (1986) first coined the term adaptive expertise and contrast it with routine expertise. They conceptualize that both types of expertise comprise the same extent of domain knowledge and the ability to perform flawless in familiar situations. However, the difference becomes apparent once confronted with an unfamiliar situation: A situation in which the task, method or desired results are not known in advance Various authors studying adaptive expertise have provided numerous descriptions with features that fall apart in three groups. First, adaptive expertise entails all the basic components of routine expertise (e.g., The focus on 'change' distinguishes research on adaptive expertise from research on expert performance. The latter type of research tries to identify individuals who perform on a superior level on tasks representative for their domain Research on professional expertise distinguishes itself from traditional expertise research by perceiving expertise as a developmental process observable through the problem-solving skills of individuals (Tynjälä, Nuutinen, Eteläpelto, Starting from our preliminary description of adaptive expertise and how research on adaptive expertise differs from expert performance research, a systematic literature review was conducted to detail characteristics of adaptive expertise and the environments in which individuals with a high level of adaptive expertise excel. We aim to answer four research questions. To create a well-founded conceptual understanding of adaptive expertise, the aim of the first two questions is to pinpoint which learning and personality-related factors are characteristic for adaptive expertise and not for routine expertise: 1. What learner characteristics (knowledge, skills, regulation processes, and past experience) influence adaptive expertise? 2. What personality factors influence adaptive expertise? The goal of the latter questions is to discover which environmental factors benefit behaviors indicating adaptive expertise: 3. What task and training characteristics (e.g., instruction, task complexity) influence adaptive expertise? 4. What characteristics of the learning climate (e.g., tolerance of mistakes, supervision) influence adaptive expertise?	1	\N	411	2025-06-14 12:09:51.6095
fca91beb-df8e-435d-bd13-8cff96d5144f	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	methodology	3	To answer the research questions a systematic review has been done. This method has been chosen for its transparency and reproducible process The abstracts of the complete set of articles were scanned for exclusion criteria. Of the retrieved articles, 53 did not deal with the topic of adaptive expertise or adaptive performance or did not describe how it was measured. Those articles discussed topics such as adaptive expert systems, adaptive market/company performance, or performance judgments. Other exclusion criteria were: Lack of realistic work or learning environment as these did not provide accurate task and training characteristics (3), conceptual paper (26) as these did not provide empirical evidence for characteristics of adaptive expertise or its development, suggestion of adaptive expertise as an explanation of reported findings but not as the object of study (3), and studied outcomes of adaptive expertise but not antecedents (5). Excluded were also book reviews, conference and symposium abstracts (6), and articles in languages other than English (2). Four articles could not be accessed and one article contained the same data set as discussed in another article. Of the 124 articles originally retrieved 21 eventually matched the inclusion criteria.	2	\N	192	2025-06-14 12:09:51.6095
\.


--
-- TOC entry 3535 (class 0 OID 16449)
-- Dependencies: 218
-- Data for Name: paper_selections; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.paper_selections (id, paper_id, is_selected, selected_timestamp) FROM stdin;
68257c05-d1ab-45c0-909d-a5a1efedad04	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	t	2025-06-14 12:53:24.890292
\.


--
-- TOC entry 3532 (class 0 OID 16396)
-- Dependencies: 215
-- Data for Name: papers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.papers (id, file_name, original_filename, upload_timestamp, processing_status, file_size, file_hash, grobid_processed, sentences_processed, od_cd_processed, pdf_deleted, error_message, tei_xml, tei_metadata, processing_completed_at, created_at) FROM stdin;
9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	dbe36801f8040db1bb8311c90e438ce00d251e116469ca5efb9a5cc15ed6da78_20250614_120946.pdf	adaptive expertise 5 page.pdf	2025-06-14 12:09:46.394955	completed	182009	dbe36801f8040db1bb8311c90e438ce00d251e116469ca5efb9a5cc15ed6da78	t	t	t	f	處理完成驗證失敗: 句子處理狀態未標記為完成	<?xml version="1.0" encoding="UTF-8"?>\n<TEI xml:space="preserve" xmlns="http://www.tei-c.org/ns/1.0" \nxmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \nxsi:schemaLocation="http://www.tei-c.org/ns/1.0 https://raw.githubusercontent.com/kermitt2/grobid/master/grobid-home/schemas/xsd/Grobid.xsd"\n xmlns:xlink="http://www.w3.org/1999/xlink">\n\t<teiHeader xml:lang="en">\n\t\t<fileDesc>\n\t\t\t<titleStmt>\n\t\t\t\t<title level="a" type="main">How experts deal with novel situations: A review of adaptive expertise</title>\n\t\t\t</titleStmt>\n\t\t\t<publicationStmt>\n\t\t\t\t<publisher>Elsevier BV</publisher>\n\t\t\t\t<availability status="unknown"><p>Copyright Elsevier BV</p>\n\t\t\t\t</availability>\n\t\t\t\t<date type="published" when="2014-04-03">3 April 2014</date>\n\t\t\t</publicationStmt>\n\t\t\t<sourceDesc>\n\t\t\t\t<biblStruct>\n\t\t\t\t\t<analytic>\n\t\t\t\t\t\t<author>\n\t\t\t\t\t\t\t<persName><forename type="first">Katerina</forename><surname>Bohle Carbonell</surname></persName>\n\t\t\t\t\t\t</author>\n\t\t\t\t\t\t<author>\n\t\t\t\t\t\t\t<persName><forename type="first">Renée</forename><forename type="middle">E</forename><surname>Stalmeijer</surname></persName>\n\t\t\t\t\t\t</author>\n\t\t\t\t\t\t<author>\n\t\t\t\t\t\t\t<persName><forename type="first">Karen</forename><forename type="middle">D</forename><surname>Könings</surname></persName>\n\t\t\t\t\t\t</author>\n\t\t\t\t\t\t<author>\n\t\t\t\t\t\t\t<persName><forename type="first">Mien</forename><surname>Segers</surname></persName>\n\t\t\t\t\t\t</author>\n\t\t\t\t\t\t<author>\n\t\t\t\t\t\t\t<persName><forename type="first">Jeroen</forename><forename type="middle">J G</forename><surname>Van Merriënboer</surname></persName>\n\t\t\t\t\t\t</author>\n\t\t\t\t\t\t<author>\n\t\t\t\t\t\t\t<affiliation key="aff0">\n\t\t\t\t\t\t\t\t<note type="raw_affiliation">Maastricht University, PO Box 616, 6200MD Maastricht, The Netherlands</note>\n\t\t\t\t\t\t\t\t<orgName type="institution">Maastricht University</orgName>\n\t\t\t\t\t\t\t\t<address>\n\t\t\t\t\t\t\t\t\t<postBox>PO Box 616</postBox>\n\t\t\t\t\t\t\t\t\t<postCode>6200MD</postCode>\n\t\t\t\t\t\t\t\t\t<settlement>Maastricht</settlement>\n\t\t\t\t\t\t\t\t\t<country key="NL">The Netherlands</country>\n\t\t\t\t\t\t\t\t</address>\n\t\t\t\t\t\t\t</affiliation>\n\t\t\t\t\t\t</author>\n\t\t\t\t\t\t<author>\n\t\t\t\t\t\t\t<affiliation key="aff1">\n\t\t\t\t\t\t\t\t<note type="raw_affiliation">Onderzoek &amp; Onderwijs, FHML, 6200MD Maastricht, The Netherlands.</note>\n\t\t\t\t\t\t\t\t<orgName type="department">Onderzoek &amp; Onderwijs</orgName>\n\t\t\t\t\t\t\t\t<orgName type="institution">FHML</orgName>\n\t\t\t\t\t\t\t\t<address>\n\t\t\t\t\t\t\t\t\t<postCode>6200MD</postCode>\n\t\t\t\t\t\t\t\t\t<settlement>Maastricht</settlement>\n\t\t\t\t\t\t\t\t\t<country key="NL">The Netherlands</country>\n\t\t\t\t\t\t\t\t</address>\n\t\t\t\t\t\t\t</affiliation>\n\t\t\t\t\t\t</author>\n\t\t\t\t\t\t<title level="a" type="main">How experts deal with novel situations: A review of adaptive expertise</title>\n\t\t\t\t\t</analytic>\n\t\t\t\t\t<monogr>\n\t\t\t\t\t\t<title level="j" type="main">Educational Research Review</title>\n\t\t\t\t\t\t<title level="j" type="abbrev">Educational Research Review</title>\n\t\t\t\t\t\t<idno type="ISSN">1747-938X</idno>\n\t\t\t\t\t\t<imprint>\n\t\t\t\t\t\t\t<publisher>Elsevier BV</publisher>\n\t\t\t\t\t\t\t<biblScope unit="volume">12</biblScope>\n\t\t\t\t\t\t\t<biblScope unit="page" from="14" to="29"/>\n\t\t\t\t\t\t\t<date type="published" when="2014-04-03">3 April 2014</date>\n\t\t\t\t\t\t</imprint>\n\t\t\t\t\t</monogr>\n\t\t\t\t\t<idno type="MD5">0C64B75080B6218272C487852A58E1C0</idno>\n\t\t\t\t\t<idno type="DOI">10.1016/j.edurev.2014.03.001</idno>\n\t\t\t\t\t<note type="submission">Received 25 October 2013 Revised 26 March 2014 Accepted 27 March 2014</note>\n\t\t\t\t</biblStruct>\n\t\t\t</sourceDesc>\n\t\t</fileDesc>\n\t\t<encodingDesc>\n\t\t\t<appInfo>\n\t\t\t\t<application version="0.8.0" ident="GROBID" when="2025-06-14T12:09+0000">\n\t\t\t\t\t<desc>GROBID - A machine learning software for extracting information from scholarly documents</desc>\n\t\t\t\t\t<ref target="https://github.com/kermitt2/grobid"/>\n\t\t\t\t</application>\n\t\t\t</appInfo>\n\t\t</encodingDesc>\n\t\t<profileDesc>\n\t\t\t<textClass>\n\t\t\t\t<keywords>Adaptive expertise Individual factors Environmental factors Review</keywords>\n\t\t\t</textClass>\n\t\t\t<abstract>\n<div xmlns="http://www.tei-c.org/ns/1.0"><p>Adaptive expertise allows individuals to perform at a high level in the face of changing job tasks and work methods, setting it apart from routine expertise. Given the increased need for flexibility in the workplace, adaptive expertise is increasingly important for today's graduates and professionals. This review investigates which individual and environmental factors distinguish adaptive expertise from routine expertise and thus provides insights into how to facilitate adaptive expertise and its development. Key differences between routine and adaptive expertise are related to knowledge representation, cognitive and analogical problem solving abilities, and past experiences. Learning and working environments, which give individuals the responsibility to develop their own solution strategy and have supportive superiors benefit adaptive expertise. The results of our review also indicate that there is little consensus on the degree of adaptation adaptive expertise provides and the characteristics of a novel situation.</p></div>\n\t\t\t</abstract>\n\t\t</profileDesc>\n\t</teiHeader>\n\t<facsimile>\n\t\t<surface n="1" ulx="0.0" uly="0.0" lrx="544.252" lry="742.677"/>\n\t\t<surface n="2" ulx="0.0" uly="0.0" lrx="544.252" lry="742.677"/>\n\t\t<surface n="3" ulx="0.0" uly="0.0" lrx="544.252" lry="742.677"/>\n\t</facsimile>\n\t<text xml:lang="en">\n\t\t<body>\n<div xmlns="http://www.tei-c.org/ns/1.0"><head n="1.">Introduction</head><p>Today's work environments are characterized by increasing complexity due to higher levels of required knowledge and task volatility <ref type="bibr">(Howard, 1995;</ref><ref type="bibr">Molloy &amp; Noe, 2009;</ref><ref type="bibr">Tannenbaum, 2001)</ref>. It is no longer sufficient to be an expert in one domain, but employees need to be able to combine different specializations <ref type="bibr">(Pink, 2006)</ref>, adapt to changes in their domain <ref type="bibr">(Smith, Ford, &amp; Kozlowski, 1996)</ref>, and develop their expertise and become proficient in other domains <ref type="bibr">(van der Heijden, 2002)</ref>. In short, they must be able to deal effectively with novel situations and problems. Therefore, flexibility at the workplace becomes a critical ingredient for career success <ref type="bibr">(van der Heijden, 2002)</ref>. While some people quickly overcome changes in work requirements by inventing new procedures and using their expert knowledge in novel ways <ref type="bibr">(Hatano &amp; Inagaki, 1986;</ref><ref type="bibr">Holyoak, 1991)</ref>, others do not possess this ability and find themselves thrown back performing as a novice. This ability to quickly get accustomed to change has been called adaptive expertise <ref type="bibr">(Hatano &amp; Inagaki, 1986)</ref>.</p><p>Adaptive expertise is generally seen as important, but its characteristics and development are ill understood. Achieving a better understanding of the concept of adaptive expertise is necessary to design learning activities that contribute to its development. Therefore, the aim of this systematic review is to establish what the characteristics of adaptive expertise are and with which training and task characteristics it flourishes. By analyzing the characteristics that distinguish adaptive expertise from routine expertise, it will become possible to deduct what learning activities lead to it.</p><p>Hatano and Inagaki (1986) first coined the term adaptive expertise and contrast it with routine expertise. They conceptualize that both types of expertise comprise the same extent of domain knowledge and the ability to perform flawless in familiar situations. However, the difference becomes apparent once confronted with an unfamiliar situation: A situation in which the task, method or desired results are not known in advance <ref type="bibr">(Ellström, 2001)</ref>. While individuals with routine expertise struggle with the new demands, adaptive expertise allows for easily overcoming the novelty and quickly regaining a high level of performance thanks to a knowledge representation which allows for flexibility <ref type="bibr">(Schwartz, Bransford, &amp; Sears, 2005)</ref>. In contrast to routine expertise, individuals with adaptive expertise possess the knowledge of why and under which conditions certain methods have to be used or new methods have to be devised.</p><p>Various authors studying adaptive expertise have provided numerous descriptions with features that fall apart in three groups. First, adaptive expertise entails all the basic components of routine expertise (e.g., <ref type="bibr">Fisher &amp; Peterson, 2001;</ref><ref type="bibr">Hatano &amp; Oura, 2003;</ref><ref type="bibr">Martin, Rivale, &amp; Diller, 2007;</ref><ref type="bibr">Mylopoulos &amp; Woods, 2009;</ref><ref type="bibr">Varpio, Schryer, &amp; Lingard, 2009)</ref>. Second, adaptive expertise is marked by better developed meta-cognitive skills than routine expertise (e.g., <ref type="bibr">Crawford, Schlager, Toyama, Riel, &amp; Vahey, 2005;</ref><ref type="bibr">Martin, Petrosino, Rivale, &amp; Diller, 2006)</ref>. Third, adaptive expertise is set apart through abilities such as flexibility, ability to innovate, continuous learning, seeking out challenges, and creativity (e.g., <ref type="bibr">Barnett &amp; Koslowski, 2002;</ref><ref type="bibr">Crawford et al., 2005;</ref><ref type="bibr">Hatano &amp; Oura, 2003;</ref><ref type="bibr">Martin et al., 2006</ref><ref type="bibr">Martin et al., , 2007;;</ref><ref type="bibr">Mylopoulos &amp; Scardamalia, 2008;</ref><ref type="bibr">Varpio et al., 2009)</ref>. These characteristics point to two important facets of adaptive expertise. Firstly, it develops out of routine expertise. This is based on the first characteristic and implies that both forms of expertise are observable through accurate and efficient performance on domain-relevant and familiar tasks. It is postulated that individuals with routine expertise maintain their performance but halt their learning (Chi, 2011) and thus do not further develop into the stage of adaptive expertise. Secondly, <ref type="bibr">Hatano and Inagaki (1986)</ref> suggest that adaptive expertise is after all domain-dependent because it is through accumulated experiences that adaptive expertise develops. In line with this conceptualization, researchers typically define the situation in which adaptive expertise is beneficial over routine expertise as changes in work and/or job task requirements <ref type="bibr">(Allworth &amp; Hesketh, 1999;</ref><ref type="bibr">Blickle et al., 2011;</ref><ref type="bibr">Griffin &amp; Hesketh, 2003)</ref>, changes in the complexity of situations (Chen, Thomas, &amp; Wallace, 2005), changes from usual to unusual situations <ref type="bibr">(Joung, Hesketh, &amp; Neal, 2006)</ref>, or changes from common to exceptional situations <ref type="bibr">(Neal et al., 2006)</ref>.</p><p>The focus on 'change' distinguishes research on adaptive expertise from research on expert performance. The latter type of research tries to identify individuals who perform on a superior level on tasks representative for their domain <ref type="bibr">(Ericsson, 2007;</ref><ref type="bibr">Ericsson &amp; Towne, 2010)</ref>. Through analysis of their performance on standardized tasks it is possible to identify abilities of experts within a domain. In contrast to expert performance research, the tasks with which to analyze adaptive expertise are not standardized tasks within the experts' domain, but novel tasks within or even outside their domain. Research on adaptive expertise should thus not be placed within the research tradition of expert performance research. While this research is moving away from its classical focus on chess players, musicians and sportsmen, it still focuses on analyzing the performance of individuals who have achieved a sustainable and observable streak of top performance on standardized tasks within their domain.</p><p>Research on professional expertise distinguishes itself from traditional expertise research by perceiving expertise as a developmental process observable through the problem-solving skills of individuals (Tynjälä, Nuutinen, Eteläpelto, <ref type="bibr">Kirjonen, &amp; Remes, 1997)</ref>. Another important difference is its strong focus on the social environment as a place in which learning happens. This is included in the dimensions of social recognition and growth and flexibility of professional expertise <ref type="bibr">(Van Der Heijden, 2000)</ref>. These two dimensions, a focus on development and the social environment, pinpoint the differences between expert performance and professional expertise. Adaptive expertise narrows the operationalizing lens further down by only looking at the developmental dimension of professional expertise. These differences between expert performance and adaptive expertise result in a number of characteristics of adaptive expertise research. Firstly, studied tasks need not be standardized nor representative for the domain; however, they need to represent a realistic problem. Secondly, participants are not selected for their track record of superior performance in their domain, but they should also not be novices. Ideally, they have some years of work experience. Thirdly, performance should be measured based on speed, accuracy and feasibility of proposed solutions to unfamiliar problems.</p><p>Starting from our preliminary description of adaptive expertise and how research on adaptive expertise differs from expert performance research, a systematic literature review was conducted to detail characteristics of adaptive expertise and the environments in which individuals with a high level of adaptive expertise excel. We aim to answer four research questions.</p><p>To create a well-founded conceptual understanding of adaptive expertise, the aim of the first two questions is to pinpoint which learning and personality-related factors are characteristic for adaptive expertise and not for routine expertise:</p><p>1. What learner characteristics (knowledge, skills, regulation processes, and past experience) influence adaptive expertise? 2. What personality factors influence adaptive expertise?</p><p>The goal of the latter questions is to discover which environmental factors benefit behaviors indicating adaptive expertise: 3. What task and training characteristics (e.g., instruction, task complexity) influence adaptive expertise? 4. What characteristics of the learning climate (e.g., tolerance of mistakes, supervision) influence adaptive expertise?</p></div>\n<div xmlns="http://www.tei-c.org/ns/1.0"><head n="2.">Method</head><p>To answer the research questions a systematic review has been done. This method has been chosen for its transparency and reproducible process <ref type="bibr">(Cook, Mulrow, &amp; Haynes, 1997)</ref>. A systematic review allows to discover the consistency and variation within studies in one field <ref type="bibr">(Davies, 2000)</ref> and thus to provide an exhaustive summary on the relevant studies for the research questions. To retrieve the necessary studies, the databases of Business source premier, CINAHL, Emerald Insights, Eric, MedLine, PsycArticles, and Social Sciences Citation Index were consulted. Those databases were chosen for their access to articles in the field of educational science. Articles using the term ''adaptive expertise'', ''adaptive expert'' or ''adaptive performance'' published between 1991 and 2012 were retrieved. The term adaptive performance was included, because it is the outcome of an individual trying to overcome the discrepancies between his or her behavior and the new demands created by changes in the work environment <ref type="bibr">(Chan, 2000)</ref>. As through adaptive expertise individuals overcome these discrepancies, they should demonstrate adaptive performance. In the remainder of the article, adaptive expertise will be used to describe both terms. Articles which had one of the terms in the abstract or keywords were selected. The search resulted in an output of 124 unique articles.</p><p>The abstracts of the complete set of articles were scanned for exclusion criteria. Of the retrieved articles, 53 did not deal with the topic of adaptive expertise or adaptive performance or did not describe how it was measured. Those articles discussed topics such as adaptive expert systems, adaptive market/company performance, or performance judgments. Other exclusion criteria were: Lack of realistic work or learning environment as these did not provide accurate task and training characteristics (3), conceptual paper (26) as these did not provide empirical evidence for characteristics of adaptive expertise or its development, suggestion of adaptive expertise as an explanation of reported findings but not as the object of study (3), and studied outcomes of adaptive expertise but not antecedents (5). Excluded were also book reviews, conference and symposium abstracts (6), and articles in languages other than English (2). Four articles could not be accessed and one article contained the same data set as discussed in another article. Of the 124 articles originally retrieved 21 eventually matched the inclusion criteria.</p></div>\n<div xmlns="http://www.tei-c.org/ns/1.0"><head n="3.">Results</head></div>\n<div xmlns="http://www.tei-c.org/ns/1.0"><head n="3.1.">Sample descriptive</head><p>In the articles the dependent variable was defined as adaptive expert or adaptive expertise (5), adaptive performance (15), and adaptive transfer (1). Two articles were published before 2000, 12 before 2010, and 7 after 2010. Quantitative studies were conducted 14 times and seven studies used a mixed-method approach. Ten studies were conducted at the workplace, six in an educational context, and five were simulation studies. Workplace studies were conducted in several industries (hospitality = 2; military = 1; aerospace = 1; electric power utility company = 1, and government agency = 1) and also across industries (4). The studies conducted in educational contexts dealt with experienced firefighters (2) and engineering pupils/students (4). Table <ref type="table">1</ref> provides an overview of the research questions.</p><p>Adaptive expertise has been measured through different methods. These methods are summarized in Table <ref type="table">2</ref> as performance data (objective and subjective ratings of performance) and self and peer assessment instruments.</p></div><figure xmlns="http://www.tei-c.org/ns/1.0" type="table" xml:id="tab_0"><head>4 .</head><label>4</label><figDesc>Discussion . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 26 4.1. Limitations . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 27 4.2. Future research . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 27 4.3. Implication. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 27 5. Conclusion . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 27 References . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 28</figDesc><table /></figure>\n\t\t</body>\n\t\t<back>\n\t\t\t<div type="references">\n\n\t\t\t\t<listBibl/>\n\t\t\t</div>\n\t\t</back>\n\t</text>\n</TEI>\n	{"title": null, "authors": [], "abstract": null}	\N	2025-06-14 12:09:46.394955
\.


--
-- TOC entry 3540 (class 0 OID 16533)
-- Dependencies: 223
-- Data for Name: processing_errors; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.processing_errors (id, task_id, error_type, error_code, error_message, stack_trace, context_data, severity, is_recoverable, recovery_suggestion, created_at) FROM stdin;
\.


--
-- TOC entry 3539 (class 0 OID 16519)
-- Dependencies: 222
-- Data for Name: processing_events; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.processing_events (id, task_id, event_type, event_name, message, step_number, total_steps, percentage, details, created_at) FROM stdin;
\.


--
-- TOC entry 3536 (class 0 OID 16464)
-- Dependencies: 219
-- Data for Name: processing_queue; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.processing_queue (id, paper_id, processing_stage, status, priority, retry_count, max_retries, created_at, started_at, completed_at, error_message, processing_details) FROM stdin;
\.


--
-- TOC entry 3538 (class 0 OID 16493)
-- Dependencies: 221
-- Data for Name: processing_tasks; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.processing_tasks (id, paper_id, task_id, task_type, priority, retries, max_retries, status, started_at, finished_at, timeout_seconds, data, result, error_message, user_id, parent_task_id, created_at) FROM stdin;
\.


--
-- TOC entry 3534 (class 0 OID 16427)
-- Dependencies: 217
-- Data for Name: sentences; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.sentences (id, paper_id, section_id, content, sentence_order, word_count, char_count, has_objective, has_dataset, has_contribution, detection_status, error_message, retry_count, explanation, created_at, updated_at) FROM stdin;
8ccefd0f-7a49-4213-ab75-19b811c2535d	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	Today's work environments are characterized by increasing complexity due to higher levels of required knowledge and task volatility Adaptive expertise is generally seen as important, but its characteristics and development are ill understood.	0	33	\N	f	f	f	success	\N	0	Describes the context and current understanding without defining the concept or measurement procedures.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
693e90f5-79e6-477f-bbe3-87f5a1703116	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	Achieving a better understanding of the concept of adaptive expertise is necessary to design learning activities that contribute to its development.	0	21	\N	f	f	f	success	\N	0	The sentence discusses the importance of understanding adaptive expertise for designing learning activities, but does not define what adaptive expertise is or how to measure it.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
1b6205bc-ea90-4d45-bf1d-6a91bdd78a39	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	Therefore, the aim of this systematic review is to establish what the characteristics of adaptive expertise are and with which training and task characteristics it flourishes.	0	26	\N	f	f	f	success	\N	0	The sentence states the aim of a review and does not define or specify how to measure adaptive expertise.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
9d6e01ba-412f-4433-8d10-6e9ff2984d71	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	By analyzing the characteristics that distinguish adaptive expertise from routine expertise, it will become possible to deduct what learning activities lead to it.	0	23	\N	f	f	f	success	\N	0	The sentence discusses the potential to deduce learning activities by analyzing characteristics but does not define or specify how to measure adaptive expertise.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
99f34ba3-922a-466a-9487-7a0a300adb26	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	Hatano and Inagaki (1986) first coined the term adaptive expertise and contrast it with routine expertise.	0	16	\N	f	f	f	success	\N	0	This sentence states a historical fact about the term adaptive expertise rather than defining its meaning or measurement.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
80d89d89-4058-42a3-ad45-0cef2e39541a	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	They conceptualize that both types of expertise comprise the same extent of domain knowledge and the ability to perform flawless in familiar situations.	0	23	\N	f	f	t	success	\N	0	Explains the essence of expertise by describing its fundamental components without specifying measurement methods.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
ed51285d-c207-4121-b2cc-ece55dc8b585	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	However, the difference becomes apparent once confronted with an unfamiliar situation: A situation in which the task, method or desired results are not known in advance Various authors studying adaptive expertise have provided numerous descriptions with features that fall apart in three groups.	0	43	\N	f	f	f	success	\N	0	Describes a situational contrast and mentions descriptions by authors without defining or measuring a concept.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
94c44de3-56c9-48dc-8b93-56bc62460f41	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	First, adaptive expertise entails all the basic components of routine expertise (e.	0	12	\N	f	f	t	success	\N	0	Explains the fundamental nature of adaptive expertise by relating it to routine expertise without describing measurement or procedures.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
4d73915f-992c-4bae-964a-7ca13a8a4fb6	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	g., The focus on 'change' distinguishes research on adaptive expertise from research on expert performance.	0	15	\N	f	f	f	success	\N	0	The sentence contrasts research focuses but does not explain what adaptive expertise is or how to measure it.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
49554059-0488-438c-92c3-ba9b0de23e50	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	The latter type of research tries to identify individuals who perform on a superior level on tasks representative for their domain Research on professional expertise distinguishes itself from traditional expertise research by perceiving expertise as a developmental process observable through the problem-solving skills of individuals (Tynjälä, Nuutinen, Eteläpelto, Starting from our preliminary description of adaptive expertise and how research on adaptive expertise differs from expert performance research, a systematic literature review was conducted to detail characteristics of adaptive expertise and the environments in which individuals with a high level of adaptive expertise excel.	0	93	\N	f	f	f	success	\N	0	The sentence describes research focus and methods but does not define what adaptive expertise is or specify how to measure it.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
8bdafba1-ca1f-42fb-9885-af495e95284d	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	We aim to answer four research questions.	0	7	\N	f	f	f	success	\N	0	The sentence describes an intention to answer research questions and does not define a concept or specify measurement methods.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
8c691c5d-e4fe-46f4-9c9c-26f9a63a4d22	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	To create a well-founded conceptual understanding of adaptive expertise, the aim of the first two questions is to pinpoint which learning and personality-related factors are characteristic for adaptive expertise and not for routine expertise: 1. What learner characteristics (knowledge, skills, regulation processes, and past experience) influence adaptive expertise?	0	48	\N	f	f	f	success	\N	0	Describes the aim of research questions to identify characteristics but does not define or measure adaptive expertise.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
ad5608df-771b-4d07-8bf7-4c9addd456f2	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	What personality factors influence adaptive expertise?	0	6	\N	f	f	f	success	\N	0	The sentence asks a question about factors influencing adaptive expertise without defining or measuring the concept.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
727ef94f-3768-4fbf-a38b-b48be7113e07	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	The goal of the latter questions is to discover which environmental factors benefit behaviors indicating adaptive expertise: 3.	0	18	\N	f	f	f	success	\N	0	The sentence describes a goal related to exploring environmental factors benefiting behaviors, but does not define or measure a concept directly.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
f07159a3-006d-40af-a24c-19856091ab0d	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	What task and training characteristics (e.	0	6	\N	f	f	f	success	\N	0	The sentence is incomplete and does not provide a definition or measurement procedure.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
eb307dea-bda6-43a5-ba70-d470b2e9392c	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	g., instruction, task complexity) influence adaptive expertise?	0	7	\N	f	f	f	success	\N	0	The sentence is incomplete and appears to be a fragment asking a question rather than defining a concept or measurement.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
d4993ce0-9b6c-4491-839b-bd7d048243a0	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	4. What characteristics of the learning climate (e.	0	8	\N	f	f	f	success	\N	0	The sentence is incomplete and does not provide a definition or measurement of a concept.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
a2bfc117-b1f1-4160-ac3d-31c01d90c9fb	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	0ae92e03-b5f4-429f-ba4e-19770a9ab0b4	g., tolerance of mistakes, supervision) influence adaptive expertise?	0	8	\N	f	f	f	success	\N	0	The sentence is incomplete and appears to be a question fragment, not defining or describing how to measure a concept.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
5816439c-43f2-4b0d-a9ec-3e6fe369171f	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	fca91beb-df8e-435d-bd13-8cff96d5144f	To answer the research questions a systematic review has been done.	0	11	\N	f	f	f	success	\N	0	Describes a research method used, not defining or measuring a concept.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
034abc69-4505-49df-8cde-53badff40123	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	fca91beb-df8e-435d-bd13-8cff96d5144f	This method has been chosen for its transparency and reproducible process The abstracts of the complete set of articles were scanned for exclusion criteria.	0	24	\N	t	f	f	success	\N	0	Describes the concrete procedure of scanning abstracts for exclusion criteria, indicating a specific assessment method.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
1f1703d6-a109-424f-b79a-61096e9c9b3d	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	fca91beb-df8e-435d-bd13-8cff96d5144f	Of the retrieved articles, 53 did not deal with the topic of adaptive expertise or adaptive performance or did not describe how it was measured.	0	25	\N	f	f	f	success	\N	0	The sentence describes exclusion criteria and does not define or describe how to measure a concept.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
57842929-b98b-4546-bcbb-484d96b0edf0	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	fca91beb-df8e-435d-bd13-8cff96d5144f	Those articles discussed topics such as adaptive expert systems, adaptive market/company performance, or performance judgments.	0	15	\N	f	f	f	success	\N	0	This sentence is descriptive, mentioning topics discussed without defining or specifying how to measure any concept.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
4a284643-6298-4f40-9d25-b54ec9dc9e5b	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	fca91beb-df8e-435d-bd13-8cff96d5144f	Other exclusion criteria were: Lack of realistic work or learning environment as these did not provide accurate task and training characteristics (3), conceptual paper (26) as these did not provide empirical evidence for characteristics of adaptive expertise or its development, suggestion of adaptive expertise as an explanation of reported findings but not as the object of study (3), and studied outcomes of adaptive expertise but not antecedents (5).	0	68	\N	f	f	f	success	\N	0	Describes exclusion criteria for studies and does not define or measure a concept.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
a508c539-99f0-45ae-ba5f-4c87af803a5a	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	fca91beb-df8e-435d-bd13-8cff96d5144f	Excluded were also book reviews, conference and symposium abstracts (6), and articles in languages other than English (2).	0	18	\N	f	f	f	success	\N	0	This sentence describes exclusion criteria for a study but does not define any concept or measurement procedure.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
1ade2752-161c-4855-a175-21b779c0c4ef	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	fca91beb-df8e-435d-bd13-8cff96d5144f	Four articles could not be accessed and one article contained the same data set as discussed in another article.	0	19	\N	f	f	f	success	\N	0	The sentence describes access and data duplication issues without defining or measuring a concept.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
800b9b3c-a578-4705-8208-35521799bdde	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	fca91beb-df8e-435d-bd13-8cff96d5144f	Of the 124 articles originally retrieved 21 eventually matched the inclusion criteria.	0	12	\N	f	f	f	success	\N	0	Describes a result about article selection rather than defining a concept or measurement procedure.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
c95087e4-8616-49f4-84c0-92ebee33346f	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	512941ed-3c18-462b-98a6-07f8d02f9054	In the articles the dependent variable was defined as adaptive expert or adaptive expertise (5), adaptive performance (15), and adaptive transfer (1).	0	22	\N	f	f	f	success	\N	0	Describes which variables were labeled as dependent variables in studies without defining what those concepts mean or how they are measured.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
ee5ef3e7-07ed-43c5-b46c-3e927cf0426b	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	512941ed-3c18-462b-98a6-07f8d02f9054	Two articles were published before 2000, 12 before 2010, and 7 after 2010.	0	13	\N	f	f	f	success	\N	0	The sentence describes publication counts over time but does not define or measure a concept.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
91115e5e-57c0-47ee-98df-420fb3c70ea1	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	512941ed-3c18-462b-98a6-07f8d02f9054	Quantitative studies were conducted 14 times and seven studies used a mixed-method approach.	0	13	\N	f	f	f	success	\N	0	The sentence reports study counts and methods used, but does not define or operationalize a concept.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
ac600a09-fc29-48fd-84ff-bfedeafa9b58	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	512941ed-3c18-462b-98a6-07f8d02f9054	Ten studies were conducted at the workplace, six in an educational context, and five were simulation studies.	0	17	\N	f	f	f	success	\N	0	Describes the number and context of studies conducted without defining or measuring any concept.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
f9992bbe-39f0-4d59-8268-b3e2403ea530	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	512941ed-3c18-462b-98a6-07f8d02f9054	Workplace studies were conducted in several industries (hospitality = 2; military = 1; aerospace = 1; electric power utility company = 1, and government agency = 1) and also across industries (4).	0	32	\N	f	f	f	success	\N	0	Describes the number and types of workplace studies conducted without defining or measuring a concept.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
00d1ba95-5d1f-4e20-b385-5b5eaf3b932c	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	512941ed-3c18-462b-98a6-07f8d02f9054	The studies conducted in educational contexts dealt with experienced firefighters (2) and engineering pupils/students (4).	0	15	\N	f	f	f	success	\N	0	Describes the subjects involved in studies but does not define or measure a concept.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
374daf87-a6d2-446e-862e-328673c118c9	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	512941ed-3c18-462b-98a6-07f8d02f9054	Table Adaptive expertise has been measured through different methods.	0	9	\N	f	f	f	success	\N	0	The sentence states that adaptive expertise has been measured by different methods but does not define what it is or specify any measurement procedures.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
ed2fb72a-fa92-4363-9b8f-a2d15844e74d	9718b9cb-49b4-4325-b9d9-4a1dd11c3c63	512941ed-3c18-462b-98a6-07f8d02f9054	These methods are summarized in Table	0	6	\N	f	f	f	success	\N	0	Sentence is descriptive and refers to a table summary, without defining or measuring a concept.	2025-06-14 12:09:51.6095	2025-06-14 12:09:51.6095
\.


--
-- TOC entry 3537 (class 0 OID 16482)
-- Dependencies: 220
-- Data for Name: system_settings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.system_settings (id, setting_key, setting_value, description, updated_at) FROM stdin;
89ef166a-88b2-447d-97a8-d5d68a6af459	system_version	"1.0.0"	系統版本	2025-06-14 07:48:37.455392
a7b949a9-faf4-4d46-93b7-991460041e8a	max_file_size_mb	50	最大上傳檔案大小(MB)	2025-06-14 07:48:37.455392
485a2665-b909-4d32-a498-717de0bc784b	batch_processing_size	10	批次處理句子數量	2025-06-14 07:48:37.455392
e0a1512f-18a7-4cca-bd4c-533929bf8393	auto_cleanup_hours	24	自動清理暫存檔案時間(小時)	2025-06-14 07:48:37.455392
\.


--
-- TOC entry 3542 (class 0 OID 16605)
-- Dependencies: 225
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, google_id, email, name, picture_url, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 3543 (class 0 OID 16619)
-- Dependencies: 226
-- Data for Name: workspaces; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.workspaces (id, user_id, name, created_at, updated_at) FROM stdin;
\.


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

