
import useAppStore from '../store';

export const getUserId = () => {
    let userId = useAppStore.getState().user?.id;

    if (!userId && process.env.NODE_ENV === 'development') {
        userId = 'dev-user'; // Dummy user ID for development
    }

    return userId;
};