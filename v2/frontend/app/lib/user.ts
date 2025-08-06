import useAppStore from '../store';

export const getUserId = () => {
    let userId = useAppStore.getState().user?.id;

    if (!userId && process.env.NODE_ENV === 'development') {
        userId = 'dev-user'; // Dummy user ID for development
    }

    return userId;
};

export const getToken = (): string | null => {
    if (typeof window !== 'undefined') {
        return localStorage.getItem('authToken');
    }
    return null;
};