import { FC, ComponentType } from 'react';

export interface WidgetConfig {
    apiKey: string;
    darkTheme?: boolean;
    initialOpen?: boolean;
    onEvent?: (eventName: string, data?: any) => void;
}

export interface WidgetProps {
    config: WidgetConfig;
    onClose?: () => void;
    onOpen?: () => void;
    onConfirm?: (state:boolean) => void;
    onCheck?: (state:boolean) => void;
    onSubmit?: (data: string) => void;
    widgetState: {
        isOpen: boolean;
        confirmed: boolean;
        checked: boolean;
        darkTheme: boolean;
    };
}

export interface WidgetState {
    isOpen: boolean;
    confirmed: boolean;
    darkTheme: boolean;
    checked: boolean;
}

export interface WidgetActions {
    open: () => void;
    close: () => void;
    toggle: () => void;
    submit: (data: string) => void;
    setDarkTheme: (isDark: boolean) => void;
}

export interface UseWidgetResult {
    WidgetComponent: any;
    widgetState: WidgetState;
    widgetActions: WidgetActions;
    isLoading: boolean;
    error: Error | null;
}