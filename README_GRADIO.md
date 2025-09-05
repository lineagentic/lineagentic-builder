# Data Product Composer - Gradio Web Interface

This document explains how to use the new Gradio web interface for the Data Product Composer chat application.

## Overview

The Gradio interface (`gradio_chat.py`) provides the same functionality as the command-line chat interface (`chat.py`) but with a modern web-based user interface. Users can interact with the Data Product Composer Agent through their web browser.

## Features

- **Web-based Chat Interface**: Modern, responsive chat UI
- **Session Management**: Automatic session creation and persistence
- **Real-time Status**: View current session information
- **Chat History**: Maintains conversation context
- **Clear Chat**: Reset session and start fresh
- **Error Handling**: Graceful error handling and user feedback

## Prerequisites

1. **OpenAI API Key**: Set the `OPENAI_API_KEY` environment variable
2. **Python Dependencies**: All required packages are already included in `pyproject.toml`

## Running the Gradio Interface

### Method 1: Direct Execution
```bash
python gradio_chat.py
```

### Method 2: Using uv (Recommended)
```bash
uv run gradio_chat.py
```

## Usage

1. **Start the Application**: Run the command above
2. **Open Browser**: The interface will automatically open in your default browser at `http://localhost:7860`
3. **Chat**: Type your messages in the chat input box and press Enter or click "Send"
4. **Session Management**: 
   - Click "Clear Chat" to start a new session
5. **End Session**: Close the browser tab or stop the application

## Interface Components

### Chat Area
- **Chatbot Display**: Shows conversation history with user and agent messages
- **Message Input**: Text box for typing messages
- **Send Button**: Submit your message

### Control Panel
- **Clear Chat**: Reset the conversation and start a new session

### Information Panel
- **Tips**: Helpful guidance for using the interface
- **Instructions**: Overview of what the agent can help with

## Key Differences from Command-Line Interface

| Feature | Command-Line (`chat.py`) | Web Interface (`gradio_chat.py`) |
|---------|-------------------------|----------------------------------|
| Interface | Terminal/Console | Web Browser |
| Session Management | Automatic | Manual controls |
| Error Handling | Console output | In-interface display |
| Accessibility | Local terminal | Any device with browser |
| Sharing | Local only | Can be shared via network |

## Troubleshooting

### Common Issues

1. **"Agent not initialized" Error**
   - Solution: Click "Clear Chat" to reinitialize the agent

2. **Port Already in Use**
   - Solution: The app will automatically find an available port, or you can modify the port in the code

3. **Browser Doesn't Open Automatically**
   - Solution: Manually navigate to `http://localhost:7860` in your browser

4. **API Key Issues**
   - Solution: Ensure `OPENAI_API_KEY` environment variable is set correctly

### Logs

The application creates log files:
- `dp_builder_gradio.log`: Application logs
- Console output: Real-time status messages

## Development

### Customization

You can customize the interface by modifying:
- **CSS Styling**: Update the `css` variable in `create_gradio_interface()`
- **Port and Host**: Modify the `launch()` parameters
- **Interface Layout**: Adjust the Gradio components and layout
- **Functionality**: Extend the `GradioChatInterface` class

### Adding Features

To add new features:
1. Extend the `GradioChatInterface` class with new methods
2. Add corresponding UI components in `create_gradio_interface()`
3. Connect event handlers for user interactions

## Security Notes

- The interface runs on `0.0.0.0` by default, making it accessible from other devices on your network
- For production use, consider adding authentication and HTTPS
- The `share=False` parameter prevents creating public links (set to `True` if needed)

## Support

For issues or questions:
1. Check the log files for error details
2. Verify your OpenAI API key is correctly set
3. Ensure all dependencies are installed
4. Check the console output for startup messages
