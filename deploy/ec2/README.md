# EC2-hosted database

Use this folder if your PostgreSQL database runs on an AWS EC2 instance (or RDS) instead of on your
own machine. The app itself still runs locally; it just connects to that database.

For a fully local setup instead, see `../local/README.md`.

## 1. Log in to the instance

EC2 console -> Instances -> select it -> copy the **Public IPv4 address** (it changes when the instance
is stopped and started unless you attach an Elastic IP). You need the `.pem` key from when the instance
was created. **Never commit it** (`*.pem` is git-ignored).

```bash
chmod 400 ~/path/to/your-key.pem
ssh -i ~/path/to/your-key.pem ec2-user@<public-ip>
```

Username by AMI: Amazon Linux `ec2-user`, Ubuntu `ubuntu`, Debian `admin`. No key? Use the console's
**EC2 Instance Connect** or **Session Manager**.

## 2. Find the database details (Postgres on the instance)

```bash
sudo -u postgres psql -c '\du'                       # users (roles)
sudo -u postgres psql -c '\l ehr_db'                 # database owner and access list
sudo -u postgres psql -c "SELECT rolname, rolsuper, has_database_privilege(rolname,'ehr_db','CONNECT') AS can_connect FROM pg_roles WHERE rolcanlogin;"
sudo -u postgres psql -c 'SHOW port;' -c 'SHOW listen_addresses;'
sudo -u postgres psql -d ehr_db -c '\dx'             # is pgvector installed?
sudo -u postgres psql -d ehr_db -c '\dt'             # tables
```

If `sudo -u postgres` says the user doesn't exist, Postgres may be RDS or in Docker:

```bash
systemctl status postgresql | head -3
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Ports}}'
docker inspect <container> --format '{{range .Config.Env}}{{println .}}{{end}}' | grep POSTGRES
```

**RDS:** details are in the console under RDS -> Databases -> your DB (endpoint, port, master user,
DB name), or `aws rds describe-db-instances`.

## 3. Get or reset the password

Postgres stores only a hash, so the password can't be read back. Look for where it was saved:

```bash
sudo grep -rIl --include=".env" --include="*.yml" --include="*.conf" \
  -e DB_PASSWORD -e POSTGRES_PASSWORD -e "postgresql://" / 2>/dev/null | head
cat ~/.pgpass
```

Otherwise reset it (type the new password yourself; don't paste it into chats or commit it):

```bash
sudo -u postgres psql -c "ALTER USER your_db_user WITH PASSWORD 'a-new-strong-password';"
```

Update any other app that uses this user. For RDS use **Modify -> new master password**, or fetch the
secret from Secrets Manager: `aws secretsmanager get-secret-value --secret-id <name>`.

## 4. Connect from your laptop (SSH tunnel, recommended)

Keep Postgres closed to the internet and tunnel through SSH instead of opening port 5432:

```bash
ssh -i ~/path/to/your-key.pem -N -L 5433:localhost:5432 ec2-user@<ec2-public-ip>
# RDS in a private subnet: -L 5433:<rds-endpoint>:5432  (its security group must allow the EC2 instance)
```

Leave that terminal open, then in the repository root:

```bash
cp deploy/ec2/.env.ec2.example .env     # then fill in DB_USER, DB_PASSWORD, OPENAI_API_KEY, AUDIT_HASH_KEY
python scripts/migrate.py               # once; creates tables + pgvector objects if missing
python scripts/verify_ingestion.py
uvicorn src.api.main:app --reload
```

If you connect directly instead of tunnelling, all three must be true: Postgres
`listen_addresses` includes the interface, `pg_hba.conf` allows your IP (`host all all <ip>/32 scram-sha-256`),
and the security group allows TCP 5432 **from your IP only**. Never open 5432 to `0.0.0.0/0`.

## Reminders

- The `pgvector` extension must exist (`CREATE EXTENSION vector;`); migration 002 runs it with
  `IF NOT EXISTS`, which needs a privileged user the first time.
- Patient-style data on a networked server deserves care: use the tunnel, keep the password out of git,
  and stop the instance when you're not using it.
