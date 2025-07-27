const API_BASE_URL = 'http://127.0.0.1:8000/api/v1'

export const apiService = {

    async createSubmission(text: string, keyId: string | undefined, questionResult: boolean, domain: string, pageLink: string) {
        if (!text || text.length < 10) throw new Error('Invalid text, must be longer than 10 characters')
        if (!keyId) throw new Error('Please provide an active API key')
        const create = await fetch(`${API_BASE_URL}/submissions`, {
            method: 'POST',
            headers: {
                'Content-type': 'application/json',
                'Authorization': `Bearer ${keyId}`
            },
            body: JSON.stringify({
                orig_text: text,
                question_result: questionResult,
                domain: domain,
                page_link: pageLink
            })
        })
        const createResponse = await create.json()
        if (!create.ok) throw new Error('Failed to create text. Please try again')

        return createResponse
    },

    async createWatermark(data: any, keyId: string | undefined) {
        if (!data) throw new Error('No data provided')
        if (!keyId) throw new Error('Please provide an active API key')

        const watermark = await fetch(`${API_BASE_URL}/watermarks`, {
            method: 'POST',
            headers: {
                'Content-type': 'application/json',
                'Authorization': `Bearer ${keyId}`
            },
            body: JSON.stringify({
                data: data
            })
        })
        const createResponse = await watermark.json()
        if (!watermark.ok) throw new Error('Failed to create watermark.')

        return createResponse
    }

}