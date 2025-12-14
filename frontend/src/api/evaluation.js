/**
 * 评测集相关API
 */

import request from './request'

/**
 * 获取任务的评测集
 * @param {string} taskId - 任务ID
 * @returns {Promise} 评测集数据
 */
export const getEvaluationDataset = (taskId) => {
    return request.get(`/api/tasks/${taskId}/evaluation`)
}

/**
 * 获取评测集统计信息
 * @param {string} taskId - 任务ID
 * @returns {Promise} 统计信息
 */
export const getEvaluationStats = (taskId) => {
    return request.get(`/api/tasks/${taskId}/evaluation/stats`)
}

/**
 * 下载评测集
 * @param {string} taskId - 任务ID
 * @param {string} format - 格式 (json/csv)
 * @returns {Promise} 下载响应
 */
export const downloadEvaluation = (taskId, format = 'json') => {
    return request.get(`/api/tasks/${taskId}/evaluation/download`, {
        params: { format },
        responseType: 'blob'
    })
}
