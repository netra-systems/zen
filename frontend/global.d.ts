/// <reference types="@testing-library/jest-dom" />
/// <reference types="react" />
/// <reference types="react-dom" />
import '@testing-library/jest-dom';

declare global {
  namespace JSX {
    interface IntrinsicElements {
      [elemName: string]: any;
    }
  }
}