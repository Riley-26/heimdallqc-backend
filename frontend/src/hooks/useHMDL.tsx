import React, { memo, useMemo } from 'react';
import { useState, useEffect, useCallback } from 'react';
import { HMDLWidget } from '../components/Widget';
import { WidgetConfig, UseWidgetResult, WidgetState } from '../types';

export const useHMDL = (config: WidgetConfig): UseWidgetResult => {

    // Default configuration with fallbacks
    const widgetConfig: WidgetConfig = {
        apiKey: config.apiKey,
        darkTheme: config.darkTheme,
        initialOpen: config.initialOpen || false,
        onEvent: config.onEvent || (() => { })
    };


    // State management
    const [isOpen, setIsOpen] = useState<boolean>(widgetConfig.initialOpen || false);
    const [showAlert, setShowAlert] = useState<boolean>(false);
    const [darkTheme, setDarkTheme] = useState<boolean>(true);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<Error | null>(null);
    const [content, setContent] = useState<string>()
    const [confirmed, setConfirmed] = useState<boolean>(false)
    const [checked, setChecked] = useState<boolean>(false)


    // Combined state object
    const widgetState: WidgetState = {
        isOpen,
        confirmed,
        darkTheme,
        checked,
        isLoading,
        showAlert,
        setShowAlert
    };


    // Widget control actions
    const widgetActions = {
        open: () => {
            setIsOpen(true);
            widgetConfig.onEvent?.('opened');
        },
        close: () => {
            setIsOpen(false);
            widgetConfig.onEvent?.('closed');
        },
        toggle: () => {
            setIsOpen(prev => {
                const newState = !prev;
                widgetConfig.onEvent?.(newState ? 'opened' : 'closed');
                return newState;
            });
        },
        submit: async (data: string, customId?: number) => {
            if (confirmed) {
                await createSubmission(data, customId)
                widgetConfig.onEvent?.("submitted", data);
            } else {
                console.log("please confirm")
                setShowAlert(true)
                setIsOpen(true)
            }
        },
        confirm: (state: boolean) => {
            setConfirmed(state)
            widgetConfig.onEvent?.(state ? "confirmed": "unconfirmed", state);
        },
        check: (state: boolean) => {
            setChecked(state)
            widgetConfig.onEvent?.(state ? "checked": "unchecked", state);
        },
        setDarkTheme: (isDark: boolean) => {
            setDarkTheme(isDark);
            widgetConfig.onEvent?.('theme_changed', isDark);
        }
    };


    // Create new submission
    const createSubmission = async (text: string, customId?: number) => {
        setIsLoading(true);
        setError(null);

        if (text && text.length > 10){
            const submissionResponse = await fetch(
                "http://127.0.0.1:8000/api/submissions",
                {
                    method: "POST",
                    headers: {
                        "Authorization": `Bearer ${widgetConfig.apiKey}`,
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        text: text,
                        domain: window.location.hostname,
                        custom_id: customId,
                        questionResult: checked
                    })
                }
            )

            const submissionCreated = await submissionResponse.json()
            console.log(submissionCreated)
        } 

        setIsLoading(false);
    };


    // Widget component with required props
    const WidgetComponent = () => (
        <HMDLWidget
            config={widgetConfig}
            onClose={widgetActions.close}
            onOpen={widgetActions.open}
            onConfirm={widgetActions.confirm}
            onCheck={widgetActions.check}
            onSubmit={widgetActions.submit}
            widgetState={widgetState}
        />
    )

    return {
        WidgetComponent,
        widgetState,
        widgetActions,
        isLoading,
        error
    };
};