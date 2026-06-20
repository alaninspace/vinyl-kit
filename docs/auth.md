# Authentication Guide: Discogs API

To fetch metadata and cover art from Discogs, VinylKit needs access to their API. You can authenticate in two ways: with a **Personal Access Token** (simplest) or via **OAuth 1.0a** (needed for account features like fetching your collection).

## Option 1: Personal Access Token

This is the easiest way to get started. It doesn't need a browser login flow.

1. Log in to your [Discogs Settings](https://www.discogs.com/settings/developers).
2. Click **"Generate new personal access token"**.
3. Copy the token.
4. Configure VinylKit to use it:

```bash
# Bash / PowerShell
vinylkit config set discogs_token <YOUR_TOKEN>
```

---

## Option 2: OAuth 1.0a (Browser Login)

If you want to use the interactive login flow, you first need to create a "Discogs Application" to get a Consumer Key and Secret.

### 1. Create a Discogs Application

1. Go to the [Discogs Developer Portal](https://www.discogs.com/settings/developers).
2. Click **"Create an Application"**.
3. Fill in the details (e.g., Name: "MyVinylKit", Description: "Local tagging tool").
4. Once created, you will see a **Consumer Key** and **Consumer Secret**.

### 2. Configure VinylKit with your App Credentials

Because VinylKit runs locally on your machine, you only need to set these App credentials once:

```bash
# Bash / PowerShell
vinylkit config set consumer_key <YOUR_KEY>
vinylkit config set consumer_secret <YOUR_SECRET>
```

### 3. Run the Login Command

Now you can perform the interactive login:

```bash
# Bash / PowerShell
vinylkit auth login
```

1. VinylKit will provide a URL.
2. Open the URL in your browser and click **"Authorize"**.
3. Discogs will display a **Verifier Code**.
4. Copy that code back into your terminal when prompted.

---

## Understanding Auth Modes

VinylKit can store different kinds of credentials at the same time. You can choose which one to use via the `auth_mode` setting.

### How it chooses (Auto-Priority)

By default, `auth_mode` is set to `auto`. VinylKit will look for credentials and use the most powerful one it finds in this order:

1. **Full OAuth 1.0a**: If you have completed the `auth login` flow.
2. **Personal Access Token**: If you have manually set a `discogs_token`.
3. **Key & Secret**: If you have only set `consumer_key` and `consumer_secret`.

### Manually Switching Modes

You can force VinylKit to use a specific method even if others are configured:

```bash
# Bash / PowerShell

# Force use of your Personal Access Token
vinylkit config set auth_mode token

# Force use of Full OAuth
vinylkit config set auth_mode oauth

# Switch back to automatic selection
vinylkit config set auth_mode auto
```

| Mode | Images? | Identity? | Use Case |
| :--- | :--- | :--- | :--- |
| `token` | Yes | Yes | Personal use |
| `oauth` | Yes | Yes | Account-linked features |
| `key_secret` | Yes | No | Public data retrieval without identity |
| `none` | No | No | Public data only (Low rate limit) |

---

## Migrating Credentials Between Machines

If you need to manually set up OAuth credentials from another machine, you will need the `discogs_secret` (OAuth token secret) in addition to `discogs_token`:

```bash
# Bash / PowerShell
vinylkit config set discogs_token <YOUR_TOKEN>
vinylkit config set discogs_secret <YOUR_SECRET>
vinylkit config set consumer_key <YOUR_KEY>
vinylkit config set consumer_secret <YOUR_SECRET>
vinylkit config set auth_mode oauth
```

## Verifying Authentication

To check which mode is active and if your credentials are valid:

```bash
# Bash / PowerShell
vinylkit config show
vinylkit auth identity
```

---

## See Also

- **[Configuration Guide](configuration.md)** — Full list of all settings including auth-related keys.
- **[User Guide](user-guide.md)** — Command reference and workflows.
