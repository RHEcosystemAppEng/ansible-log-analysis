# Ansible Log Analysis Quick Start

Welcome to the Ansible log analysis Quick Start! a system that automatically detects errors, classifies them by authorization level, and generates intelligent step-by-step solutions. Our system eliminates manual log searching and reduces resolution time by routing issues to the appropriate experts.

## Table of Contents

1. [Overview](#overview)
2. [Problem We Solve](#problem-we-solve)
3. [Current Manual Process](#current-manual-process)
4. [Our Solution Stack](#our-solution-stack)
5. [High-Level Solution](#high-level-solution)
6. [Agentic Workflow](#agentic-workflow)
   - [Step 1: Embedding and Clustering](#step-1-embedding-and-clustering)
   - [Step 2: Summary and Expert Classification per Log Template](#step-2-summary-and-expert-classification-per-log-template)
   - [Step 3: Creating a step-by-step solution](#step-3-creating-a-step-by-step-solution)
   - [Step 4: Store the data](#step-4-store-the-data)
   - [Training and Inference stages](#training-and-inference-stages)
7. [User Interface](#user-interface)
8. [Annotation Interface](#annotation-interface)
9. [Requirements](#requirements)
   - [Software Requirements](#software-requirements)
   - [Minimum Hardware Requirements](#minimum-hardware-requirements)
10. [Deployment](#deployment)
    - [Quick Start - Local Development](#quick-start---local-development)
    - [Deploy on the Cluster](#deploy-on-the-cluster)

## Problem We Solve

**The Challenge:** Organizations running Ansible automation at scale face significant challenges when errors occur. Log analysis is manual, time-consuming, and requires specialized knowledge across multiple domains (AWS, Kubernetes, networking, etc.). When failures happen, teams spend valuable time searching through logs, identifying the right experts, and waiting for solutions.

**Our Solution:** An AI-powered log analysis system that automatically:
- Detects and categorizes Ansible errors in real-time
- Routes issues to appropriate experts based on authorization levels
- Provides contextual, step-by-step solutions using AI agents
- Learns from historical resolutions to improve future recommendations

## Current Manual Process

A human analyst is:

* Searching for error logs.  
* Talk with the person who is authorized with the credentials to solve the problem:  
  * Examples:   
    AWS provisioning failed requires talking with the AWS person who is authorized.  
    Bug in the playbook source code \- talk with the programmer.  
* The authenticated person needs to **understand how to solve the problem**.  
* Solve the problem.

## Our Solution Stack

* Loki \- as a log database.  
* Alloy/Promtail \- log ingestion and label definer.  
* OpenShiftAI \- model serving, data science pipeline, notebooks.  
* Backend:  
  * FASTAPI \- for api endpoints.  
  * Langchain.  
  * LangGraph \- for building the agentic workflow.  
  * PostgreSQL.  
  * Sentence Transformers \- generating embeddings.  
* UI:  
  * Gradio (for now)  
* Annotation interface: an interface that is used for evaluation and workflow improvement  
  * Gradio

## High-Level Solution

1. Data is being **ingested** from the Red Hat Ansible Automation Platform (AAP) clusters, using Alloy or Promtail, into Loki (a time series database designed for logs).  
2. An **error log is alerted** using a Grafana alert and sent into the agentic workflow.  
3. The **agentic workflow** processes the log and stores the processed data into a PostgreSQL database.  
4. The log analyst using the **UI** interacts with the logs and gets suggestions on how to solve the error, depending on their authorization. 

<img src="figures/high_level_architecture.png" alt="high_level_architecture" style="width:65%;">

## Agentic Workflow:

<img src="figures/workflow.png" alt="Workflow" style="width:65%;">

### Step 1: Embedding and Clustering

Many logs are generated from the same log template. To group them, we embed a subset of each log, then cluster all the embeddings into groups. Each group represents a log template. For example, let’s look at the following three logs:

```
1. error: user id 10 already exits.
2. error: user id 15 already exits.
3. error: password of user itayk is wrong.
```

As we can see here, logs 1 and 2 are from the same template, and we want to group them together.

Then the user will be able to filter by templates.

### Step 2: Summary and Expert Classification per Log Template

For each log template, create a summary of the log and classify it by authorization.  
For example, an analyst who has AWS authentication will filter by their authorization and will see only relevant error summaries in the UI.

### Step 3: Creating a step-by-step solution 

We will have a router that will determine if we need more context to solve the problem or if the log error alone is sufficient to generate the step-by-step solution.  
If we need more context, we will spin up an agent that will accumulate context as needed by using the following:

* **Loki MCP**, which is able to query the log database for additional log context.  
* **RAG** for retrieving an error cheat sheet of already solved questions.  
* **Ansible MCP** for obtaining code source data to suggest a better solution.

### Step 4: Store the data

* Store a payload of the generated values for each log in a PostgreSQL database.

### Training and Inference stages

Currently, the **only difference** between the training and inference stages is the clustering algorithm.

#### Training

Train the clustering algorithm to cluster the logs by log-template.

#### Inference 

Load the trained clustering model.

## User Interface

* Each expert selects their rule, dependent on their authorization. Current rules are:  
  * Kubernetes / OpenShift Cluster Admins  
  * DevOps / CI/CD Engineers (Ansible \+ Automation Platform)  
  * Networking / Security Engineers  
  * System Administrators / OS Engineers  
  * Application Developers / GitOps / Platform Engineers  
  * Identity & Access Management (IAM) Engineers  
  * Other / Miscellaneous  
* Each expert can filter by labels (cluster\_name, log\_file\_name, …)  
* A summary of each log is listed to the expert, the expert can click on the log summary and view the whole log, and a step-by-step solution, timestamp, and labels

<img src="figures/experts_option.png" alt="Experts Option" style="width:40%;">

After selecting the authorization class "expert":

<img src="figures/ui_view.png" alt="UI View" style="width:65%;">

<img src="figures/step-by-step.png" alt="Step-by-step Solution" style="width:65%;">

## Annotation Interface

For improving our agentic workflow, context PDFs, and other context we need to understand the errors. To do so, we have a data annotation interface for annotating Ansible error log pipeline outputs,  
Where we see the agentic workflow:

* **Input** of the left (error log)  
* **Outputs** in the center (summary, and step-by-step solution)  
* **Annotation window** on the right.

See the interface below:

<img src="figures/anotation_interface.png" alt="Annotation Interface" style="width:65%;">

## Requirements

### Software Requirements

#### For Production Cluster Deployment
- **OpenShift Cluster** <TODO add version>
- **Helm** <TODO add version>
- **oc CLI** (for OpenShift)


### Minimum Hardware Requirements

#### Production Cluster Environment

<TODO>


#### Scalability Considerations

<TODO>
- **GPU** for faster embedding.


## Deployment

The Ansible Log Monitor can be deployed in multiple environments depending on your needs. Choose the deployment method that best fits your requirements:

### Mock Data (Temporary for Development)

To use add data during development, add your log files to the `data/logs/failed` directory. 

Each log should be saved as a separate `.txt` file (e.g., `<filename>.txt`).
For example `data/logs/failed/example.txt`

### Quick Start - Local Development

For development and testing, you can run all services locally using the provided Makefile:

#### Prerequisites
- Docker and Docker Compose
- `uv` package manager with Python 3.12+
- Make (for running deployment commands)
- Make sure you have added the mock data as described in the [### Mock Data (Temporary for Development)](#mock-data-temporary-for-development) section.

#### Deploy Locally

Follow these steps to set up and run the Ansible Log Monitor on your local development environment:

**1. Clone and Setup Repository**
```bash
# Clone the repository
git clone <repository-url>
cd ansible-logs

# Install Python dependencies using uv
uv sync
```

**2. Configure Environment Variables**
```bash
# Copy the environment template and configure your settings
cp .env.example .env

# Edit .env with your API keys and configuration:
# - OPENAI_API_ENDPOINT: VLLM (OpenAI) compitable endpoint (some endpoint need to add /v1 as suffix)
# - OPENAI_API_TOKEN: your token to the endpoint
# - OPENAI_MODEL: Model to use (e.g., Granite-3.3-8B-Instruct	)
# - LANGSMITH_API_KEY: Optional, for LangSmith tracing
```

**3. Start All Services**
In short:
```bash
make local/start
make local/run-whole-training-pipeline
```

```bash
# Launch all services in the background
make local/start

# Run the complete training pipeline (do it after local/start)
make local/run-whole-training-pipeline

# Perform status check to see which services are running
make local/status

# Stop all services when done
make local/stop
```

**Additional Commands**
```bash
# Restart all services
make local/restart

# View all available local commands
make local/help
```

### Deploy on the Cluster

!!!
NOTE currently you must to create a secret in the namesapce named `model-secret` with the values:
OPENAI_API_TOKEN = <your MaaS token>
OPENAI_API_ENDPOINT = <your MaaS endpoint>
!!!

For production deployment on OpenShift clusters:

#### Prerequisites
- OpenShift CLI (`oc`) installed and configured
- Helm 3.x installed
- Access to an OpenShift cluster
- MaaS API Token for AI services

#### Quick Deployment
```bash
# Install the application (uses current OpenShift project)
make deploy/install OPENAI_API_TOKEN=your-token-here

# With custom namespace
make deploy/install NAMESPACE=ansible-logs-monitor OPENAI_API_TOKEN=your-token-here
```

#### Access Services
```bash
# Forward UI to localhost:7860
make deploy/port-forward-ui

# Forward Backend API to localhost:8000
make deploy/port-forward-backend

# Forward Annotation Interface to localhost:7861
make deploy/port-forward-annotation

# Forward Grafana to localhost:3000
make deploy/port-forward-grafana
```

#### Uninstall
```bash
# Remove from current project
make deploy/uninstall

# Remove from specific namespace
make deploy/uninstall NAMESPACE=ansible-logs-monitor
```

For detailed configuration options and troubleshooting, see [deploy/helm/README.md](deploy/helm/README.md).

