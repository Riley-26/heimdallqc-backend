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
    onConfirm?: (state:boolean) => void;
    confirmed?: boolean;
    onCheck?: (state:boolean) => void;
    checked?: boolean;
    onSubmit?: (data: string) => void;
}

export interface WidgetState {
    isOpen: boolean;
    confirmed: boolean;
    theme: 'light' | 'dark';
    checked: boolean;
}

export interface WidgetActions {
    open: () => void;
    close: () => void;
    toggle: () => void;
    submit: (data: string) => void;
    setTheme: (theme: 'light' | 'dark') => void;
    setText: (data: string) => void;
}

export interface UseWidgetResult {
    WidgetComponent: any;
    widgetState: WidgetState;
    widgetActions: WidgetActions;
    isLoading: boolean;
    error: Error | null;
}