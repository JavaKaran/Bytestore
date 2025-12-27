'use client';

import { ReactNode } from 'react';
import { useUploadCleanup } from '@/lib/hooks/useUploadCleanup';

interface UploadCleanupProviderProps {
    children: ReactNode;
}

/**
 * Provider component that runs upload cleanup on app initialization.
 * Wrap your app with this to automatically clean up stale uploads.
 */
export function UploadCleanupProvider({ children }: UploadCleanupProviderProps) {
    // Run cleanup on mount
    useUploadCleanup();

    return <>{children}</>;
}

