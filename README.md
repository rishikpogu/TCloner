# Automated Telegram Channel Cloner

This is a GitHub Template for creating a fully automated, resumable clone of any public or private Telegram channel/group you have access to. It runs on a schedule using GitHub Actions, so you can "set it and forget it."

The cloner is designed for perfect fidelity, preserving replies, media albums, and message formatting without the "Forwarded from" tag, making your clone a perfect mirror of the original.

## ✨ Core Features

*   **As-Is Cloning**: Replicates messages exactly as they appear in the source. Replies, media groups (albums), text formatting, and other entities are perfectly preserved.
*   **No "Forwarded From" Tag**: Messages are re-created in the destination, not simply forwarded. The clone appears as an original source.
*   **🔄 Resumable & Incremental**: On its first run, it clones the entire history. On all subsequent runs, it intelligently picks up where it left off, only cloning new messages.
*   **⚙️ GitHub Actions Automation**: The entire process is automated to run on a schedule (e.g., every hour) directly within GitHub. No server or personal computer needs to be running.
*   **🔒 Secure by Design**: Your sensitive credentials (`API_ID`, `API_HASH`, and `SESSION_STRING`) are stored using GitHub's encrypted secrets and are never exposed in the code or logs.
*   **🍴 Public Template**: This repository is a template. Fork it, configure it in a few simple steps, and you'll have your own private cloner running in minutes.

## 🤔 How It Works

The cloner leverages the power of the **Telethon** library to interact with Telegram's API as a user, not a bot. This is what allows it to access private channels and perform high-fidelity cloning.

1.  **Authentication**: The script uses a pre-generated `SESSION_STRING` to log into your Telegram account securely, without ever needing your password or 2FA codes in the repository.
2.  **State Management**: To make the cloning resumable, the script saves the ID of the last successfully processed message into a `state.json` file.
3.  **Reply & Group Mapping**: To preserve replies and media groups, the script maintains a mapping of `source_message_id` -> `destination_message_id` in an `id_map.json` file. This ensures that when a message is a reply, it correctly replies to the corresponding message in your new channel.
4.  **Scheduled Execution**: A GitHub Actions workflow runs the Python script on a configurable schedule. After a successful run, it automatically commits the updated `state.json` and `id_map.json` files back to your repository, ensuring the next run knows where to continue.

## 🚀 Setup Guide

Follow these steps to get your automated cloner up and running.

### Step 1: Fork This Repository

Click the **"Use this template"** or **"Fork"** button at the top of this page to create your own copy.

> **⚠️ Security Recommendation:** After forking, go to your new repository's **Settings** and set its visibility to **Private**. This protects your `state.json` and `id_map.json` files, which contain metadata about your cloned channels.

### Step 2: Get Your Telegram API Credentials

1.  Log into your Telegram account at [my.telegram.org](https://my.telegram.org).
2.  Go to the **"API development tools"** section.
3.  Create a new application (you can fill in any app name/short name).
4.  You will be given your `api_id` and `api_hash`. Copy these and keep them safe.

### Step 3: Generate Your Session String

You need to run a simple Python script **on your own computer** to generate a session string. This is the most secure way, as your credentials never leave your machine.

1.  **Clone your forked repository** to your local computer.
    ```
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```
2.  **Install the required library**:
    ```
    pip install telethon
    ```
3.  **Run the session generator script**:
    ```
    python generate_session.py
    ```
4.  The script will prompt you for your `api_id`, `api_hash`, phone number, and any login codes Telegram sends you.
5.  After successful login, it will print a long **session string**. Copy this entire string.

### Step 4: Configure GitHub Secrets

1.  In your forked GitHub repository, navigate to **Settings > Secrets and variables > Actions**.
2.  Click **New repository secret** and add the following three secrets:

| Name             | Value                                 |
| ---------------- | ------------------------------------- |
| `API_ID`         | Your `api_id` from Step 2.            |
| `API_HASH`       | Your `api_hash` from Step 2.          |
| `SESSION_STRING` | The session string you copied in Step 3. |

### Step 5: Configure Your Channels

1.  Find the IDs for your source and destination channels/groups. A simple way is to forward a message from each chat to a bot like `@userinfobot` or `@RawDataBot`.
    *   For channels and supergroups, the ID will be a long number starting with `-100`.
2.  In your repository, edit the `config.ini` file.
3.  Replace the placeholder values with your actual IDs:
    ```
    [telegram]
    source_channel_id = -100... # ❗️ Replace with your Source Channel/Group ID
    destination_channel_id = -100... # ❗️ Replace with your Destination Channel/Group ID
    ```
4.  Commit and push the changes to your repository.

### Step 6: Activate the Workflow

1.  Go to the **Actions** tab in your repository.
2.  You will see a workflow named **"Telegram Channel Cloner"**. Click on it.
3.  Click the **"Enable workflow"** button.
4.  The workflow is scheduled to run hourly, but you can trigger the first run manually. Click **"Run workflow"**, then click the green **"Run workflow"** button.

**That's it!** Your cloner is now active. You can check the **Actions** tab to see the progress of each run.

## 🔧 Troubleshooting

*   **Workflow Fails on `Run the cloner script`**:
    *   Check that your `API_ID`, `API_HASH`, and `SESSION_STRING` secrets are correctly set.
    *   Ensure the channel IDs in `config.ini` are correct and that your user account is a member of both the source and destination.
*   **Authentication Errors (`telethon.errors.rpcerrorlist...`)**:
    *   Your `SESSION_STRING` might be invalid or expired. Re-run the `generate_session.py` script locally and update the secret in GitHub.
*   **`PeerIdInvalidError`**:
    *   This usually means a channel/group ID in `config.ini` is incorrect. Double-check them.

## 📜 License

This project is open-source and available under the [MIT License](LICENSE).
