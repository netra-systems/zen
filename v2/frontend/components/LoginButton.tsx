import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';

const LoginButton = () => {
  const { login, logout, user } = useAuth();

  return (
    <div>
      {user ? (
        <Button onClick={logout} size="lg">Logout</Button>
      ) : (
        <Button onClick={login} size="lg">Login with Google</Button>
      )}
    </div>
  );
};

export default LoginButton;
