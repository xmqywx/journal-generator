# Environment Variables Setup Guide

This guide explains how to configure environment variables for the backtest system.

## Quick Start

1. **Copy the example file:**
   ```bash
   cd /Users/ying/Documents/Kris/quant/quant_v3/live
   cp .env.example .env
   ```

2. **Edit `.env` with your settings:**
   ```bash
   nano .env  # or use your preferred editor
   ```

3. **Configure PostgreSQL database:**

   For **Homebrew PostgreSQL on macOS** (typical setup):
   ```
   DATABASE_URL=postgresql://your_username@localhost:5432/quant_backtest
   ```

   For **PostgreSQL with password**:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/quant_backtest
   ```

4. **Generate a secure SECRET_KEY:**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Copy the output and paste it into your `.env` file.

5. **Initialize the database:**
   ```bash
   cd /Users/ying/Documents/Kris/quant/quant_v3/live
   python -m backtest.database
   ```

## Environment Variables Reference

### Database Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `postgresql://{USER}@localhost:5432/quant_backtest` | PostgreSQL connection string |

**Format:** `postgresql://[username]:[password]@[host]:[port]/[database]`

**Examples:**
- Local without password: `postgresql://myuser@localhost:5432/quant_backtest`
- With password: `postgresql://myuser:mypass@localhost:5432/quant_backtest`
- Remote: `postgresql://user:pass@db.example.com:5432/quant_backtest`

### Flask Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLASK_ENV` | No | `development` | Flask environment (development/production) |
| `SECRET_KEY` | Yes | - | Secret key for sessions and security |

### Backtest Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MAX_CONCURRENT_BACKTESTS` | No | `3` | Maximum concurrent backtest executions |
| `CACHE_EXPIRY_DAYS` | No | `30` | Number of days to keep cached price data |

### SocketIO Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SOCKETIO_ASYNC_MODE` | No | `threading` | SocketIO async mode (threading/eventlet/gevent) |

### Logging

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |

## Database Setup

### Prerequisites

1. **Install PostgreSQL:**

   On macOS with Homebrew:
   ```bash
   brew install postgresql@14
   brew services start postgresql@14
   ```

2. **Create database:**
   ```bash
   createdb quant_backtest
   ```

### Initialize Tables

Run the database initialization script:
```bash
cd /Users/ying/Documents/Kris/quant/quant_v3/live
python -m backtest.database
```

You should see:
```
正在初始化回测系统数据库...
✓ 数据库表创建成功！
创建的表:
  - backtest_runs (回测运行记录)
  - backtest_results (回测结果汇总)
  - backtest_trades (回测交易明细)
  - price_data_cache (历史价格数据缓存)
```

### Verify Database Connection

Test your database connection:
```bash
psql -d quant_backtest -c "\dt"
```

You should see the four tables listed.

## Security Best Practices

1. **Never commit `.env` files** - They contain sensitive credentials
2. **Use strong SECRET_KEY** - Generate with `secrets.token_hex(32)`
3. **Restrict database access** - Use firewall rules for production
4. **Rotate credentials** - Change passwords periodically
5. **Use read-only users** - For analytical queries when possible

## Troubleshooting

### "connection refused" error

**Solution:** Start PostgreSQL service
```bash
brew services start postgresql@14
```

### "database does not exist" error

**Solution:** Create the database
```bash
createdb quant_backtest
```

### "authentication failed" error

**Solution:** Check your DATABASE_URL credentials
- Verify username/password are correct
- For Homebrew PostgreSQL, password might not be needed
- Try: `postgresql://$(whoami)@localhost:5432/quant_backtest`

### "SECRET_KEY not set" warning

**Solution:** Generate and set SECRET_KEY in `.env`
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Production Deployment

For production environments:

1. **Use environment-specific files:**
   - `.env.development`
   - `.env.staging`
   - `.env.production`

2. **Set FLASK_ENV=production:**
   ```
   FLASK_ENV=production
   ```

3. **Use strong database passwords:**
   ```
   DATABASE_URL=postgresql://app_user:strong_random_password@localhost:5432/quant_backtest
   ```

4. **Enable connection pooling:**
   Already configured in `database.py`:
   - `pool_size=5`
   - `max_overflow=10`
   - `pool_pre_ping=True`

5. **Consider using connection string from secrets manager:**
   - AWS Secrets Manager
   - HashiCorp Vault
   - Environment variables from hosting platform

## Docker Configuration

If using Docker, pass environment variables:

```dockerfile
# docker-compose.yml
services:
  app:
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/quant_backtest
      - SECRET_KEY=${SECRET_KEY}

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=quant_backtest
      - POSTGRES_PASSWORD=password
```

## Support

For issues or questions:
1. Check this guide's Troubleshooting section
2. Review `/Users/ying/Documents/Kris/quant/quant_v3/live/docs/BACKTEST_GUIDE.md`
3. Check application logs for error details
