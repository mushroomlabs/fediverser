### Fediverser - bring content and users from legacy social media networks into the fediverse.

## Overview

Fediverser is a Python/Django application designed to pull data from
multiple social networks (initially Reddit, but the idea can be extend
to other legacy networks as well), and create bot accounts to mirror
the original accounts on a corresponding fediverse-enabled server.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [License](#license)

## Prerequisites

Before you begin, ensure you have met the following requirements:

- **Docker and Docker Compose**: You need to have Docker and Docker Compose installed on your system. If you haven't installed them yet, please follow the official Docker installation instructions for your platform.

- **API Access Tokens**: Obtain API access tokens for the social networks you want to mirror. For Reddit, you will need a Reddit API access token.

- **Lemmy Instance *exclusive* for bots**: to run your own reddit mirror, you will need to have a Lemmy instance that is closed for registrations and with access to the database directly. Given that Lemmy has no admin frontend to create bots, fediverser has opted to manage users by creating the records directly.

## Installation

1. Clone the Fediverser repository:

   ```bash
   git clone https://github.com/mushroomlabs/fediverser.git
   ```

2. Change to the project directory:

   ```bash
   cd fediverser
   ```

3. Create a `.env` file in the project root based on the provided `.env.example` file. This file will store your API access tokens and other configuration settings.

4. Open `.env` and fill in the required information:


   - `FEDIVERSER_REDDIT_CLIENT_ID`: Your Reddit API client ID.
   - `FEDIVERSER_REDDIT_CLIENT_SECRET`: Your Reddit API client secret.
   - `FEDIVERSER_CONNECTED_LEMMY_INSTANCE`: The domain of your fediverse instance (e.g., lemmy.example.com).
   - `FEDIVERSER_PORTAL_URL`: The url for your portal site (which your users will use to actually sign up to Lemmy)

## Usage

The included docker-compose file was created to help during
development. It already defines a lemmy instance that can be used as
the mirror and you need to provide the config.hjson and nginx.conf
(TODO: add sample files). Once these are in place, you should be able
to start the services.

1. Start the Fediverser application using Docker Compose:

   ```bash
   docker-compose up -d
   ```

1. You can access the Fediverser web interface (a basic Django admin site) will be available on `http://localhost:8000`, and the instance should be accessible on `http://localhost:8888`.

1. In order to test federation, you will need to serve this on the public web, from a real domain and serving via HTTPS. For this, the easiest solution I've found at the moment would be run something like Cloudflare Tunnel connected to `https://localhost:8888`.

## Security

- Ensure that your API access tokens and configuration files are kept secure and not exposed to unauthorized users.

- Follow the terms of service and API usage policies of the social networks and the fediverse instance to avoid any violations.

## License

This project is licensed under the [GNU Affero General Public License (AGPL)](LICENSE-AGPL-3.0). Feel free to use, modify, and distribute it according to the terms of the license.

**Note**: Be responsible when using this software. Respect the privacy and terms of service of the social networks and the fediverse instance you interact with. This software is intended for educational and research purposes and should not be used for any malicious activities.
