# Deploy the Backend to Railway with Railway MySQL

This guide deploys the Lab Storage Management FastAPI backend and a MySQL
database to Railway. It is written for an SDE beginner who has run the project
locally but may not have deployed a cloud application before.

The result will be:

```text
Browser, frontend, or API client
              |
              | HTTPS
              v
    Railway FastAPI service
              |
              | Railway private network
              v
       Railway MySQL service
```

This guide covers the backend only. The React frontend can be deployed later.

## 1. Understand the Deployment Workflow

Railway will perform these operations in order:

1. Pull the backend code from GitHub.
2. Detect Python and install the dependencies from `pyproject.toml` and
   `uv.lock`.
3. Run `uv run alembic upgrade head` as a pre-deploy command.
4. Start FastAPI with Uvicorn.
5. Call `/health/ready` before sending traffic to the new deployment.

The Alembic command is required. This application does not create or update
database tables during FastAPI startup.

## 2. Before You Start

You need:

- A GitHub account with access to this repository.
- A Railway account.
- A local clone of the repository for the one-time administrator command.
- Git installed locally.
- A terminal application.
- A credit card only if you choose a paid Railway plan.

Confirm that the local repository is current and clean:

```bash
cd /path/to/lab-storage-management
git switch main
git pull --ff-only origin main
git status --short --branch
```

Expected result:

```text
## main...origin/main
```

Do not continue from a branch containing uncommitted deployment experiments.

## 3. Set a Spending Limit First

Railway charges for the resources used by both the API and MySQL services. The
Hobby plan has a monthly minimum, and the final charge can be higher if the two
services use more than the included amount.

As of 2026-08-17, Railway documents these beginner-relevant plan rules:

- New users can start with a one-time trial credit.
- The Free plan includes a small monthly resource credit and strict resource
  limits.
- The Hobby plan costs $5 per month and includes the first $5 of resource usage.
- If Hobby resource usage is more than $5, the total bill increases to the
  actual usage amount.

An always-running API plus MySQL may exceed the Free plan or the Hobby included
usage. Treat the current prices as a starting point, not a guaranteed quote, and
check the linked Railway pricing page before deployment. Serverless sleeping can
reduce API compute, but it does not automatically stop database resource usage.

Before creating resources:

1. Open the Railway workspace dashboard.
2. Open **Usage**.
3. Select **Set Usage Limits**.
4. Add a low custom email alert.
5. Add a hard compute limit that matches your personal budget.
6. Read the warning before saving the hard limit.

When the hard limit is reached, Railway takes workloads offline. A hard limit
controls cost, but it can make the API and database unavailable. Do not use an
aggressively low limit for an application that other people depend on.

For a learning deployment, review the Usage page after the first day and again
after one week.

## 4. Create an Empty Railway Project

1. Sign in at [Railway](https://railway.com/).
2. Select **New Project**.
3. Select **Empty Project**.
4. Name the project `lab-storage-management`.
5. Keep the default environment named `production`.

Starting with an empty project lets you create MySQL before the API attempts its
first successful deployment.

## 5. Add Railway MySQL

1. Open the new project's canvas.
2. Select **+ New**.
3. Select **Database**.
4. Select **Add MySQL**.
5. Wait until the MySQL service reports that it is running.
6. Keep the service name `MySQL` for this guide.

Open the MySQL service and select **Variables**. Confirm that Railway created
these variables:

- `MYSQLHOST`
- `MYSQLPORT`
- `MYSQLUSER`
- `MYSQLPASSWORD`
- `MYSQLDATABASE`
- `MYSQL_URL`

Do not copy these secret values into the repository, a screenshot, a chat
message, or this guide.

### Keep MySQL private

The API and database are in the same Railway project, so they can communicate
over Railway's private network.

- Do not add public access to MySQL.
- Do not use `MYSQL_PUBLIC_URL` in the API service.
- Do not create a TCP proxy unless you later have a specific reason to connect
  from outside Railway.

Private networking avoids unnecessary exposure and network egress charges.

## 6. Add the FastAPI Service from GitHub

1. Return to the project canvas.
2. Select **+ New**.
3. Select **GitHub Repo**.
4. If requested, authorize Railway to read the repository.
5. Select the `lab-storage-management` repository.
6. Select the `main` branch.
7. Add the service to the project.
8. Rename the new service to `api`.

The first automatic deployment may fail because the API variables have not been
configured yet. That is expected. Do not create a second API service.

Open the `api` service and verify its source settings:

- Repository: `lab-storage-management`
- Branch: `main`
- Root directory: `/` or blank, meaning the repository root

Do not set the root directory to `front-end`. The Python backend, `pyproject.toml`,
`uv.lock`, `alembic.ini`, `migrations`, and `src` all live at the repository root.

## 7. Configure API Variables

Open the `api` service, select **Variables**, and add the following variables.
Use the Railway Raw Editor if that is easier.

```env
APP_NAME=Lab Storage Management API
DEBUG=false
RAILPACK_PYTHON_VERSION=3.11
DATABASE_URL=mysql+pymysql://${{MySQL.MYSQLUSER}}:${{MySQL.MYSQLPASSWORD}}@${{MySQL.MYSQLHOST}}:${{MySQL.MYSQLPORT}}/${{MySQL.MYSQLDATABASE}}
TOKEN_TTL_MINUTES=60
LOGIN_MAX_ATTEMPTS=5
LOGIN_WINDOW_MINUTES=15
LOGIN_LOCK_MINUTES=15
CORS_ORIGINS=
```

Important details:

- Enter the values without surrounding quotation marks.
- `MySQL` in `${{MySQL.VARIABLE}}` is the database service name and is
  case-sensitive. If you renamed the database service, replace `MySQL` with its
  exact service name.
- Use the full `mysql+pymysql://` prefix. The application uses SQLAlchemy with
  the PyMySQL driver. A plain `mysql://` URL can cause a missing MySQL driver
  error.
- The reference variables keep database credentials synchronized without
  copying their resolved secret values into the API service.
- Leave `CORS_ORIGINS` empty while testing only with curl, an API client, or the
  backend's own `/docs` page.

Review and deploy the staged variable changes when Railway prompts you.

## 8. Configure Build and Deployment Commands

Open the `api` service and select **Settings**.

### Build

Use Railway's default Railpack builder.

- Builder: **Railpack**
- Custom build command: leave blank

Railpack detects this repository as Python because it contains `pyproject.toml`.
It detects `uv` because the repository contains both `pyproject.toml` and
`uv.lock`.

### Pre-deploy command

Under the deployment settings, set:

```bash
uv run alembic upgrade head
```

This command applies every committed database migration before the new API
version starts. If the migration fails, Railway must stop the deployment instead
of starting the new API against the wrong schema.

Do not add `bootstrap-admin` to the pre-deploy command. Administrator bootstrap
is a one-time operation and intentionally refuses to run again after an
administrator exists.

### Start command

Set the custom start command to:

```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Why each part matters:

- `src.main:app` points Uvicorn to the FastAPI application in this repository.
- `--host 0.0.0.0` allows Railway's proxy to reach the process.
- `${PORT:-8000}` uses Railway's injected port and provides `8000` only as a
  fallback.

Railpack's generic FastAPI default assumes `main:app`, which is not the module
path used by this repository. Keep the custom start command.

### Healthcheck

Set the healthcheck path to:

```text
/health/ready
```

Keep the default timeout of 300 seconds for the first deployment.

`/health/ready` returns `200` only when:

- FastAPI is running.
- MySQL is reachable.
- The database is at the Alembic revision expected by the application.

The simpler `/health` endpoint checks only the API process. Use `/health/ready`
for deployment readiness.

### Serverless sleeping

Leave serverless sleeping disabled for the first deployment. Enabling it can
reduce cost for an inactive learning service, but it adds cold-start behavior
that makes the first troubleshooting session less clear. Experiment with it
only after the deployment works reliably.

## 9. Deploy the API

After saving the settings:

1. Open the `api` service's **Deployments** tab.
2. Select **Redeploy** for the latest deployment, or deploy the staged changes.
3. Open the build and deployment logs.
4. Wait for the deployment to report **Success**.

The log sequence should show:

1. Python and dependency installation.
2. Alembic upgrading the database to the latest revision.
3. Uvicorn starting successfully.
4. Railway receiving a successful healthcheck response.

Do not treat a successful build as a successful deployment. The Uvicorn process,
database migration, and healthcheck must all succeed.

## 10. Generate a Public API Domain

Railway services are not public until a domain is created.

1. Open the `api` service.
2. Open **Settings**.
3. Find **Networking**.
4. Select **Generate Domain**.
5. Copy the generated HTTPS URL.

It will look similar to:

```text
https://lab-storage-api-production.up.railway.app
```

The exact hostname will be different. Save it as your API base URL, without a
trailing slash.

For terminal examples, set:

```bash
API_URL="https://replace-with-your-domain.up.railway.app"
```

## 11. Verify Health and API Documentation

Check process health:

```bash
curl --fail --show-error "$API_URL/health"
```

Expected response:

```json
{"status":"ok"}
```

Check database readiness:

```bash
curl --fail --show-error "$API_URL/health/ready"
```

Expected response for this repository version:

```json
{"status":"ready","database":"ok","migration":"20260812_0004"}
```

Open the interactive API documentation in a browser:

```text
https://replace-with-your-domain.up.railway.app/docs
```

Stop and troubleshoot before creating the administrator if `/health/ready`
does not return `200`.

## 12. Create the First Administrator Once

The application requires a one-time command to create its first administrator.
The public registration endpoint creates viewer accounts, not administrators.

### 12.1 Choose temporary bootstrap values

Choose values that meet these rules:

- Username: 3-30 characters, starts with a letter, and contains only letters,
  numbers, or underscores.
- Email: a valid email address.
- Password: 8-72 characters with at least one letter and one number.

Do not use the sample password below as a real password.

### 12.2 Add temporary variables

Open `api` -> **Variables** and add:

```env
BOOTSTRAP_ADMIN_USERNAME=initial_admin
BOOTSTRAP_ADMIN_EMAIL=replace-with-your-email@example.com
BOOTSTRAP_ADMIN_PASSWORD=replace-with-a-long-unique-password1
```

Deploy the staged variable changes and wait for the API to become healthy again.

### 12.3 Install and authenticate the Railway CLI

Install the Railway CLI using one of these methods:

```bash
brew install railway
```

or, with Node.js 16 or newer:

```bash
npm install --global @railway/cli
```

Confirm installation and sign in:

```bash
railway --version
railway login
```

The login command opens a browser. Complete the sign-in flow there.

### 12.4 Link the local repository to the API service

From the repository root:

```bash
cd /path/to/lab-storage-management
railway link
```

The CLI stores local project-link metadata in `.railway/`. This repository
ignores that directory. Do not force-add it to Git.

When prompted, select:

- The correct workspace.
- Project: `lab-storage-management`.
- Environment: `production`.
- Service: `api`.

Verify the link:

```bash
railway status
```

### 12.5 Run the one-time bootstrap command

Run the command inside the deployed API container:

```bash
railway ssh --service api -- uv run python -m src.cli bootstrap-admin
```

The first SSH connection may ask you to register a local SSH key. Follow the
prompt, then run the command again if necessary.

Expected output:

```text
Created administrator initial_admin (id=1).
```

The numeric ID can be different.

If the command says that an administrator already exists, do not attempt to
bypass the protection. Verify whether the environment was initialized earlier.

### 12.6 Remove the bootstrap secrets

After the command succeeds:

1. Return to `api` -> **Variables**.
2. Delete all three `BOOTSTRAP_ADMIN_*` variables.
3. Deploy the staged variable changes.
4. Confirm `/health/ready` still returns `200`.

The application no longer needs these values after the first administrator is
created. Removing them reduces the lifetime of sensitive credentials.

## 13. Verify Administrator Login

Test login with the administrator username and password:

```bash
curl --fail --show-error \
  --request POST \
  --header "Content-Type: application/json" \
  --data '{"username":"initial_admin","password":"replace-with-your-real-password"}' \
  "$API_URL/users/login"
```

Expected response shape:

```json
{
  "user": {
    "id": 1,
    "username": "initial_admin",
    "email": "replace-with-your-email@example.com",
    "role": "admin",
    "profile_picture": null
  },
  "token": "an-opaque-bearer-token"
}
```

Do not paste the returned token into source control or documentation. It is a
credential.

You can also use `/docs`:

1. Open `POST /users/login`.
2. Select **Try it out**.
3. Submit the administrator credentials.
4. Copy the returned token.
5. Select **Authorize** at the top of the page.
6. Enter the bearer token as requested by the generated documentation.
7. Call `GET /users/me` and confirm that the role is `admin`.

## 14. Configure CORS When the Frontend Is Deployed

Do this only after the frontend has a real HTTPS origin.

For a frontend deployed at:

```text
https://lab-storage.example.com
```

set the API variable to:

```env
CORS_ORIGINS=https://lab-storage.example.com
```

Rules:

- Use the frontend origin, not the API origin.
- Do not include a path such as `/login`.
- Do not add a trailing slash.
- Separate multiple allowed origins with commas.
- Do not use `*` for this authenticated application.

After changing `CORS_ORIGINS`, deploy the staged change and retest login from the
browser frontend.

## 15. Normal Update Workflow

After the initial setup, a normal backend update is:

1. Make and test a code change locally.
2. Commit the change.
3. Push or merge it to `main`.
4. Railway builds the new revision automatically.
5. Railway runs `uv run alembic upgrade head`.
6. Railway starts the new API revision.
7. Railway calls `/health/ready`.
8. Railway activates the new deployment only after readiness succeeds.

Check the deployment logs after every migration change.

Important: rolling back application code does not automatically reverse a
database migration. Never run `alembic downgrade` on the cloud database without
reviewing the migration and making a backup.

## 16. Logs and Basic Operations

View logs in the dashboard from `api` -> **Deployments** -> the selected
deployment.

With the Railway CLI:

```bash
railway logs --service api
```

Show project status:

```bash
railway status
```

Open an interactive shell in the API container:

```bash
railway ssh --service api
```

Use SSH for a specific diagnostic or one-time command. Do not make permanent code
changes inside a running container because a later deployment replaces the
container filesystem.

## 17. Troubleshooting

### `DATABASE_URL` is missing

Symptoms:

- The process exits during import.
- Logs mention a Pydantic validation error for `database_url`.

Checks:

1. Confirm `DATABASE_URL` is defined on the `api` service, not only on MySQL.
2. Confirm the variable changes were deployed.
3. Confirm the variable name uses uppercase letters exactly.

### `No module named MySQLdb`

Cause:

The connection URL probably begins with `mysql://`, which makes SQLAlchemy look
for a different default driver.

Fix:

Use:

```text
mysql+pymysql://...
```

### MySQL hostname cannot be resolved

Checks:

1. Confirm the database service is running.
2. Confirm the API and MySQL services are in the same Railway project and
   environment.
3. Confirm `DATABASE_URL` references `${{MySQL.MYSQLHOST}}`.
4. Confirm `MySQL` matches the exact database service name.
5. Confirm the API is not using `MYSQL_PUBLIC_URL`.

### The migration command cannot connect

Checks:

1. Confirm MySQL is running before redeploying the API.
2. Confirm all five MySQL component variables are referenced in `DATABASE_URL`.
3. Open the pre-deploy logs, not only the Uvicorn logs.
4. Redeploy the existing API service after fixing the variables.

### `/health` succeeds but `/health/ready` returns `503`

Meaning:

FastAPI is running, but the database is unreachable or is not at the expected
Alembic revision.

Checks:

1. Read the pre-deploy migration logs.
2. Confirm `uv run alembic upgrade head` completed successfully.
3. Confirm the API and database use the same `DATABASE_URL` configuration during
   pre-deploy and runtime.

Do not replace the healthcheck with `/health` merely to hide this failure.

### Railway reports that the application failed to respond

Checks:

1. Confirm the start command includes `--host 0.0.0.0`.
2. Confirm the start command uses `${PORT:-8000}`.
3. Confirm the module path is `src.main:app`.
4. Read the first exception above the Uvicorn shutdown message.

### `bootstrap-admin` reports missing secrets

Checks:

1. Confirm all three `BOOTSTRAP_ADMIN_*` variables are set on `api`.
2. Confirm the staged variables were deployed before opening SSH.
3. Confirm SSH targets the `api` service in the `production` environment.

### `bootstrap-admin` is refused

This normally means an administrator already exists or the username/email is
already in use. The protection is intentional. Do not edit the database manually
to bypass it.

### Browser requests fail but curl works

This is usually a CORS configuration problem.

Checks:

1. Copy the frontend origin exactly from the browser address bar.
2. Remove paths and trailing slashes.
3. Update `CORS_ORIGINS` on `api`.
4. Deploy the staged variable change.
5. Inspect the browser Network tab for the actual request origin and response.

## 18. Backups and Data Safety

Railway's MySQL template runs MySQL with persistent storage, but persistence is
not a substitute for a backup.

Before using real or important data:

1. Review Railway's native volume backup options for your plan.
2. Create a backup schedule.
3. Test restoring a backup into a non-production environment.
4. Record who is allowed to access Railway and the database.
5. Do not store regulated, patient, confidential, or irreplaceable laboratory
   data in this learning deployment without an approved security and recovery
   plan.

## 19. Pause or Delete the Learning Environment

Stopping the API does not automatically remove MySQL costs. Deleting the API
does not delete the database, and deleting the database does not necessarily
remove every other project resource.

Before cleanup:

1. Decide whether the data must be preserved.
2. Create and verify a backup if necessary.
3. Record the API domain and relevant settings if the exercise will be repeated.

To remove the environment completely, delete the `api` service, then delete the
MySQL service and its volume, then verify the project canvas and Usage page.

Deleting MySQL and its volume is destructive and can permanently remove the
database. Read Railway's confirmation screen carefully.

## 20. Delivery Checklist

The deployment is complete only when every item below is true:

- [ ] The Railway project contains exactly one `api` service and one MySQL
      service for this environment.
- [ ] MySQL is not publicly exposed.
- [ ] `DATABASE_URL` uses `mysql+pymysql://` and Railway reference variables.
- [ ] `DEBUG=false`.
- [ ] The pre-deploy command is `uv run alembic upgrade head`.
- [ ] The start command points to `src.main:app` and listens on Railway's port.
- [ ] The healthcheck path is `/health/ready`.
- [ ] The public HTTPS domain works.
- [ ] `/health` returns `200`.
- [ ] `/health/ready` returns `200` and the expected migration revision.
- [ ] `/docs` loads.
- [ ] The first administrator was created successfully.
- [ ] The temporary `BOOTSTRAP_ADMIN_*` variables were removed.
- [ ] Administrator login works.
- [ ] `CORS_ORIGINS` is empty or contains only the exact deployed frontend
      origins.
- [ ] A Railway usage alert or hard limit is configured.
- [ ] A backup decision has been recorded before storing important data.

## Railway References

These Railway documents were checked while preparing this guide on 2026-08-17:

- [Deploy a FastAPI app](https://docs.railway.com/guides/fastapi)
- [Railway MySQL](https://docs.railway.com/databases/mysql)
- [Variables and reference variables](https://docs.railway.com/variables)
- [Railway variable reference](https://docs.railway.com/variables/reference)
- [Railpack Python support](https://railpack.com/languages/python/)
- [Pre-deploy commands](https://docs.railway.com/deployments/pre-deploy-command)
- [Healthchecks](https://docs.railway.com/deployments/healthchecks)
- [Railway CLI](https://docs.railway.com/cli)
- [`railway ssh`](https://docs.railway.com/cli/ssh)
- [Pricing plans](https://docs.railway.com/pricing/plans)
- [Cost control](https://docs.railway.com/pricing/cost-control)
