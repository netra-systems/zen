import { useState, useEffect, RefObject } from 'react';
import { MESSAGE_INPUT_CONSTANTS } from '../types';

const { MAX_ROWS, LINE_HEIGHT } = MESSAGE_INPUT_CONSTANTS;

export const useTextareaResize = (
  textareaRef: RefObject<HTMLTextAreaElement>,
  message: string
) => {
  const [rows, setRows] = useState(1);

  const calculateRows = (scrollHeight: number): number => {
    return Math.min(Math.ceil(scrollHeight / LINE_HEIGHT), MAX_ROWS);
  };

  const updateTextareaHeight = (element: HTMLTextAreaElement): void => {
    element.style.height = 'auto';
    const scrollHeight = element.scrollHeight;
    element.style.height = `${scrollHeight}px`;
  };

  const handleResize = (): void => {
    if (!textareaRef.current) return;
    
    const element = textareaRef.current;
    updateTextareaHeight(element);
    const newRows = calculateRows(element.scrollHeight);
    setRows(newRows);
  };

  useEffect(() => {
    handleResize();
  }, [message]);

  return { rows };
};