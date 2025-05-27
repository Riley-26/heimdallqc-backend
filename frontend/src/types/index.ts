import { FC, ComponentType } from 'react';

export interface WidgetConfig {
    apiKey: string;
    theme?: 'light' | 'dark' | 'auto';
    initialOpen?: boolean;
    apiUrl?: string;
    onEvent?: (eventName: string, data?: any) => void;
}

export interface WidgetProps {
    config: WidgetConfig;
    isOpen?: boolean;
    onClose?: () => void;
    onOpen?: () => void;
    onConfirm?: (confirmed:boolean) => void;
    onSubmit?: (data: string) => void;
}

export interface WidgetState {
    isOpen: boolean;
    confirmed: boolean;
    theme: 'light' | 'dark';
}

export interface WidgetActions {
    open: () => void;
    close: () => void;
    toggle: () => void;
    submit: (data: string) => void;
    setTheme: (theme: 'light' | 'dark') => void;
    setText: (text: string) => void;
}

export interface UseWidgetResult {
    WidgetComponent: any;
    widgetState: WidgetState;
    widgetActions: WidgetActions;
    isLoading: boolean;
    error: Error | null;
}