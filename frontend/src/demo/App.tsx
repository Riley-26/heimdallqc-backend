import React from 'react';
import ReactDOM from 'react-dom/client';
import { HmdlClient, HmdlWidget } from 'heimdallqc';
import 'heimdallqc/dist/heimdallqc.css'

const App: React.FC = () => {
    const hmdl = new HmdlClient({
        apiKey:"WW4bgYVtK9VqHDgN7b7rH6q1xSEqZBxB3ssgXCslKH2NYZwJ",
        baseUrl:"https://webhook.site/a7aae2e5-3730-49c6-adfd-5046b5640782"
    })

    const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault()
        const textarea = e.currentTarget.elements.namedItem('inputText') as HTMLTextAreaElement
        if (textarea) {
            if (!hmdl.hasConfirmed()) {
                hmdl.setErrorPopup(true)
                return
            } else {
                const analysis = hmdl.analyse(textarea.value)
                console.log(analysis)
            }
        }
    }

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "72px", justifyContent: "center", alignItems: "center" }}>
            <form onSubmit={(e) => handleSubmit(e)}>
                <textarea
                    name="inputText"
                    style={{ width: "500px", height: "200px" }}
                />
                <button type="submit">Submit</button>
            </form>
            <HmdlWidget 
                key={hmdl.key}
                client={hmdl}
                theme={'dark'}
                defaultExpanded={true}
            />
        </div>
    )
}

export default App;