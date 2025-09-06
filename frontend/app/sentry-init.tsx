'use client';

import * as Sentry from "@sentry/react";
import { useEffect } from 'react';

export function SentryInit() {
  useEffect(() => {
    Sentry.init({
      dsn: "https://1455df5778baf04bccacfee456ce3d01@o4509974514106368.ingest.us.sentry.io/4509974515023872",
      // Setting this option to true will send default PII data to Sentry.
      // For example, automatic IP address collection on events
      sendDefaultPii: true,
      integrations: [
        Sentry.browserTracingIntegration(),
        Sentry.replayIntegration({
          maskAllText: false,
          blockAllMedia: false,
        }),
      ],
      // Performance Monitoring
      tracesSampleRate: 1.0, // Capture 100% of the transactions in development
      // Session Replay
      replaysSessionSampleRate: 0.1, // This sets the sample rate at 10%. You may want to change it to 100% while in development and then sample at a lower rate in production.
      replaysOnErrorSampleRate: 1.0, // If you're not already sampling the entire session, change the sample rate to 100% when sampling sessions where errors occur.
    });
  }, []);

  return null;
}