import { C1Chat, ThemeProvider } from '@thesysai/genui-sdk';
import '@crayonai/react-ui/styles/index.css';

export const ChatPage = () => {
  // Custom message processor to include auth token
  const processMessage = async ({ threadId, messages, responseId, abortController }: {
    threadId: string;
    messages: { id: string; role: 'user' | 'assistant'; content: string }[];
    responseId: string;
    abortController: AbortController;
  }) => {
    const userMessage = messages[messages.length - 1];

    // Always get the latest token from localStorage (it may have been refreshed)
    const accessToken = localStorage.getItem('access_token');

    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        threadId,
        responseId,
        prompt: {
          id: userMessage.id,
          role: userMessage.role,
          content: userMessage.content,
        },
      }),
      signal: abortController.signal,
    });

    return response;
  };

  return (
    <div className="h-screen w-full overflow-hidden">
      <ThemeProvider mode="dark">
        <C1Chat processMessage={processMessage} />
      </ThemeProvider>
    </div>
  );
};
