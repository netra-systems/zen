
import { WebSocketProvider } from '../contexts/WebSocketContext';

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return <WebSocketProvider>{children}</WebSocketProvider>;
}
