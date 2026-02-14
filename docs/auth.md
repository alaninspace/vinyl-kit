# Authentication Guide: Discogs API

VinylKit requires access to the Discogs API to fetch metadata and images. You can authenticate in two ways: using a **Personal Access Token** (simplest) or via **OAuth 1.0a** (required for full identity features).

## Option 1: Personal Access Token (Recommended)

This is the fastest way to get started. It doesn't require a browser-based login flow.

1.  Log in to your [Discogs Settings](https://www.discogs.com/settings/developers).
2.  Click **"Generate new personal access token"**.
3.  Copy the token.
4.  Configure VinylKit to use it:
    ```bash
    # Bash / PowerShell
    vinylkit config set discogs_token <YOUR_TOKEN>
    ```

---

## Option 2: OAuth 1.0a (Browser Login)

If you prefer to use the interactive login flow, you must first create a "Discogs Application" to get a Consumer Key and Secret.

### 1. Create a Discogs Application
1.  Go to the [Discogs Developer Portal](https://www.discogs.com/settings/developers).
2.  Click **"Create an Application"**.
3.  Fill in the details (e.g., Name: "MyVinylKit", Description: "Local tagging tool").
4.  Once created, you will see a **Consumer Key** and **Consumer Secret**.

### 2. Configure VinylKit with your App Credentials
Since VinylKit is a local tool, you need to provide these credentials once:

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

1.  VinylKit will provide a URL.
2.  Open the URL in your browser and click **"Authorize"**.
3.  Discogs will display a **Verifier Code**.
4.  Copy that code back into your terminal when prompted.

---

## Understanding Auth Modes

VinylKit can store multiple types of credentials at once. You can control which one is used via the `auth_mode` setting.

### How it chooses (Auto-Priority)
By default, `auth_mode` is set to `auto`. VinylKit will look for credentials and use the most powerful one it finds in this order:

1.  **Full OAuth 1.0a**: If you have completed the `auth login` flow.
2.  **Personal Access Token**: If you have manually set a `discogs_token`.
3.  **Key & Secret**: If you have only set `consumer_key` and `consumer_secret`.

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

| Mode | Images? | Identity? | Best For... |
| :--- | :--- | :--- | :--- |
| `token` | Yes | Yes | Fast setup, personal use |
| `oauth` | Yes | Yes | 3rd-party app feel, full account access |
| `key_secret`| Yes | No | Quick testing without account identity |
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
