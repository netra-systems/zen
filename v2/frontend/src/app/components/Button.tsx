
import React from 'react';
import { RefreshCw } from 'lucide-react';

const Button = ({ children, onClick, type = 'button', disabled, isLoading, variant = 'primary', icon: Icon, className = '' }: {
    children: React.ReactNode;
    onClick?: () => void;
    type?: 'button' | 'submit' | 'reset';
    disabled?: boolean;
    isLoading?: boolean;
    variant?: 'primary' | 'secondary' | 'ghost';
    icon?: React.ElementType;
    className?: string;
}) => {
    const baseClasses = 'w-full inline-flex justify-center items-center px-4 py-2 border text-sm font-medium rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors duration-200';
    const variantClasses = {
        primary: 'border-transparent text-white bg-indigo-600 hover:bg-indigo-700 focus:ring-indigo-500 disabled:bg-indigo-400 disabled:cursor-not-allowed',
        secondary: 'border-gray-300 text-gray-700 bg-white hover:bg-gray-50 focus:ring-indigo-500 disabled:bg-gray-100 disabled:cursor-not-allowed',
        ghost: 'border-transparent text-gray-500 hover:bg-gray-100 hover:text-gray-700 focus:ring-indigo-500',
    };
    return (
        <button type={type} onClick={onClick} disabled={disabled || isLoading} className={`${baseClasses} ${variantClasses[variant]} ${className}`}>
            {isLoading ? <RefreshCw className="animate-spin -ml-1 mr-3 h-5 w-5" /> : (Icon && <Icon className="-ml-1 mr-3 h-5 w-5" />)}
            {children}
        </button>
    );
};

export default Button;
