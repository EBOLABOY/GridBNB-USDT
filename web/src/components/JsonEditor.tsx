/**
 * JSON 编辑器组件
 * 基于 Monaco Editor，支持语法高亮、格式化、验证
 */

import React, { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { Button, Space, message } from 'antd';
import { FormatPainterOutlined, CheckOutlined } from '@ant-design/icons';

interface JsonEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  height?: string | number;
  readOnly?: boolean;
  theme?: 'vs-dark' | 'light';
}

const JsonEditor: React.FC<JsonEditorProps> = ({
  value = '',
  onChange,
  height = 300,
  readOnly = false,
  theme = 'vs-dark',
}) => {
  const [editorValue, setEditorValue] = useState(value);
  const [isValid, setIsValid] = useState(true);

  useEffect(() => {
    setEditorValue(value);
  }, [value]);

  // 验证 JSON 格式
  const validateJson = (text: string): boolean => {
    if (!text.trim()) {
      return true; // 空值也认为是有效的
    }
    try {
      JSON.parse(text);
      return true;
    } catch {
      return false;
    }
  };

  // 处理编辑器变化
  const handleEditorChange = (newValue: string | undefined) => {
    const val = newValue || '';
    setEditorValue(val);
    setIsValid(validateJson(val));
    onChange?.(val);
  };

  // 格式化 JSON
  const handleFormat = () => {
    try {
      const parsed = JSON.parse(editorValue);
      const formatted = JSON.stringify(parsed, null, 2);
      setEditorValue(formatted);
      setIsValid(true);
      onChange?.(formatted);
      message.success('格式化成功');
    } catch (error) {
      message.error('JSON 格式错误，无法格式化');
    }
  };

  // 压缩 JSON
  const handleMinify = () => {
    try {
      const parsed = JSON.parse(editorValue);
      const minified = JSON.stringify(parsed);
      setEditorValue(minified);
      setIsValid(true);
      onChange?.(minified);
      message.success('压缩成功');
    } catch (error) {
      message.error('JSON 格式错误，无法压缩');
    }
  };

  return (
    <div>
      {!readOnly && (
        <div style={{ marginBottom: 8 }}>
          <Space>
            <Button
              size="small"
              icon={<FormatPainterOutlined />}
              onClick={handleFormat}
              disabled={!isValid && editorValue.trim() !== ''}
            >
              格式化
            </Button>
            <Button
              size="small"
              onClick={handleMinify}
              disabled={!isValid && editorValue.trim() !== ''}
            >
              压缩
            </Button>
            {isValid && editorValue.trim() && (
              <span style={{ color: '#52c41a', fontSize: 12 }}>
                <CheckOutlined /> JSON 格式正确
              </span>
            )}
            {!isValid && editorValue.trim() && (
              <span style={{ color: '#ff4d4f', fontSize: 12 }}>
                ⚠ JSON 格式错误
              </span>
            )}
          </Space>
        </div>
      )}
      <Editor
        height={height}
        defaultLanguage="json"
        value={editorValue}
        onChange={handleEditorChange}
        theme={theme}
        options={{
          readOnly,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          fontSize: 13,
          lineNumbers: 'on',
          folding: true,
          automaticLayout: true,
          tabSize: 2,
        }}
      />
    </div>
  );
};

export default JsonEditor;
