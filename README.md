# coolBot
A discord bot designed for coolLabs discord community server to create support post by pinging the bot on a members message. it moves messages from general channesl to a forum channel by creating a post on the forum channel.

<br />

# Features

### Bot Trigger
When you ping the bot in a reply, it will be activated. Once triggered, the bot will delete all messages from the original sender (not the user who triggered the bot) starting from the message that initiated the trigger. 

It will then create a post in the support channel, including all messages and attachments from the conversation. 

To prevent abuse, an Authorized role has been implemented (you'll need to add the role ID to the environment variables). The bot will only be triggered if a member with the Authorized role pings it.

![Trigger](/assets/trigger.png)


### Logs
The bot sends logs whenever it is triggered and also provides startup logs.

![Logs](/assets/logs.png)


### Post 
The bot creates a post that includes user messages and attachments, and sends an embedded message with general information.

![Post](/assets/post.png)

<br />

# Development
The bot is developed in Python and can be run as a Docker container.

### 1. Clone the Repository
```sh
git clone https://github.com/ShadowArcanist/coolbot
```

### 2. Configure Environment Variables
Rename `env.example` to `.env` and fill in the required values.

### 3. Build and Run the Docker Container
```sh
docker build -t coolbot . && docker run --env-file .env coolbot
```

# Licence
This project is licensed under the Apache Version 2.0 License - see the [LICENSE](https://github.com/ShadowArcanist/coolbot/blob/master/LICENSE) file for details
