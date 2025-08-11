import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

let idCounter = 0;

export function generateUniqueId(prefix: string = 'msg'): string {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 9);
  const counter = idCounter++;
  
  if (idCounter > 999999) {
    idCounter = 0;
  }
  
  return `${prefix}_${timestamp}_${counter}_${random}`;
}
