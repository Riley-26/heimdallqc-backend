import React, { memo, useMemo } from "react"
import { useState, useEffect, useCallback } from "react"
import { HMDLWidget } from "../components/Widget"
import { WidgetConfig, UseWidgetResult, WidgetState } from "../types"
import { apiService } from "../services/apiService"

export const useHMDL = (config: WidgetConfig): UseWidgetResult => {
    // Default configuration with fallbacks
    const widgetConfig: WidgetConfig = {
        apiKey: config.apiKey,
        darkTheme: config.darkTheme,
        initialOpen: config.initialOpen || false,
        onEvent: config.onEvent || (() => {}),
    }

    // State management
    const [isOpen, setIsOpen] = useState<boolean>(widgetConfig.initialOpen || false)
    const [darkTheme, setDarkTheme] = useState<boolean>(true)
    const [showAlert, setShowAlert] = useState<boolean>(false)
    const [isLoading, setIsLoading] = useState<boolean>(false)
    const [confirmed, setConfirmed] = useState<boolean>(false)
    const [checked, setChecked] = useState<boolean>(false)
    const [error, setError] = useState<Error | null>(null)

    // Combined state object
    const widgetState: WidgetState = {
        isOpen,
        confirmed,
        darkTheme,
        checked,
        isLoading,
        showAlert,
        setShowAlert,
    }

    // Widget control actions
    const widgetActions = {
        open: () => {
            setIsOpen(true)
            widgetConfig.onEvent?.("opened")
        },
        close: () => {
            setIsOpen(false)
            widgetConfig.onEvent?.("closed")
        },
        toggle: () => {
            setIsOpen((prev) => {
                const newState = !prev
                widgetConfig.onEvent?.(newState ? "opened" : "closed")
                return newState
            })
        },
        submit: async (data: string) => {
            if (confirmed) {
                const result = await createSubmission(data)
                console.log(result)
                widgetConfig.onEvent?.("submitted", data)
            } else {
                setShowAlert(true)
                setIsOpen(true)
            }
        },
        confirm: (state: boolean) => {
            setConfirmed(state)
            widgetConfig.onEvent?.(state ? "confirmed" : "unconfirmed", state)
        },
        check: (state: boolean) => {
            setChecked(state)
            widgetConfig.onEvent?.(state ? "checked" : "unchecked", state)
        },
        setDarkTheme: (isDark: boolean) => {
            setDarkTheme(isDark)
            widgetConfig.onEvent?.("theme_changed", isDark)
        },
    }

    // Create new submission
    const createSubmission = async (text: string) => {
        if (confirmed) {
            try {
                const submission = await apiService.createSubmission(text, widgetConfig.apiKey, checked, window.location.host, window.location.origin)
                //const watermark = await createWatermark(submission)
                return {
                    "submission": submission,
                    //"watermark": watermark
                }
            } catch (err: any) {
                setError(err.message)
            }
        }
    }

    const createWatermark = async (data:any) => {
        try {
            const watermark = await apiService.createWatermark(data, widgetConfig.apiKey)

            return watermark
        } catch (err: any) {
            setError(err.message)
        }
    }

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
        error,
    }
}
