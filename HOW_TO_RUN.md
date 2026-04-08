# HOW TO RUN omega-bot

## Prerequisites
Before you start running the project, ensure you have the following dependencies installed based on your platform:

### All Platforms
- [Git](https://git-scm.com/downloads)
- [Node.js](https://nodejs.org/en/download/) (version 14 or higher)

### Docker
- [Docker](https://www.docker.com/get-started)

### Windows
- [Windows Subsystem for Linux (WSL)](https://docs.microsoft.com/en-us/windows/wsl/install)

### macOS
- Homebrew (optional, but recommended) for package management

### Linux
- Build essentials (install using `sudo apt-get install build-essential`)

## Setup Steps
### Docker
1. Clone the repository:
   ```bash
   git clone https://github.com/shivampajiyar29/omega-bot.git
   cd omega-bot
   ```
2. Build the Docker image:
   ```bash
   docker build -t omega-bot .
   ```
3. Run the Docker container:
   ```bash
   docker run -it --rm omega-bot
   ```

### Windows
1. Clone the repository:
   ```bash
   git clone https://github.com/shivampajiyar29/omega-bot.git
   ```
2. Open Command Prompt or PowerShell and navigate to the project directory:
   ```bash
   cd omega-bot
   ```
3. Install dependencies:
   ```bash
   npm install
   ```
4. Run the application:
   ```bash
   npm start
   ```

### macOS
1. Clone the repository:
   ```bash
   git clone https://github.com/shivampajiyar29/omega-bot.git
   ```
2. Navigate to the project directory:
   ```bash
   cd omega-bot
   ```
3. Install dependencies:
   ```bash
   npm install
   ```
4. Run the application:
   ```bash
   npm start
   ```

### Linux
1. Clone the repository:
   ```bash
   git clone https://github.com/shivampajiyar29/omega-bot.git
   ```
2. Navigate to the project directory:
   ```bash
   cd omega-bot
   ```
3. Install dependencies:
   ```bash
   npm install
   ```
4. Run the application:
   ```bash
   npm start
   ```

## Troubleshooting
- If you encounter issues with Node.js installations, ensure the PATH variable is set correctly.
- For Docker-related issues, check if Docker is running and troubleshoot using the Docker documentation.

## Language Composition
The project is primarily written in JavaScript with Node.js and utilizes Express.js for the backend. Ensure you have a compatible Node.js version for optimal performance.

Happy coding!