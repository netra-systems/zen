import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Message, SubAgentStatus } from '@/types';

interface ChatState {
  messages: Message[];
  subAgentStatus: SubAgentStatus | null;
  error: string | null;
}

const initialState: ChatState = {
  messages: [],
  subAgentStatus: null,
  error: null,
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    addMessage(state, action: PayloadAction<Message>) {
      state.messages.push(action.payload);
    },
    setSubAgentStatus(state, action: PayloadAction<SubAgentStatus>) {
      state.subAgentStatus = action.payload;
    },
    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload;
    },
  },
});

export const { addMessage, setSubAgentStatus, setError } = chatSlice.actions;

export default chatSlice.reducer;
