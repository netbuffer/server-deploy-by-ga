const fs = require('fs');
const https = require('https');
const crypto = require('crypto');
const path = require('path');

function sendDingTalk() {
  const webhook = process.env.DINGTALK_WEBHOOK;
  const secret = process.env.DINGTALK_SECRET;

  if (!webhook) {
    console.log('⚠️ DINGTALK_WEBHOOK 未配置，跳过钉钉通知发送。');
    return;
  }

  // 优先在 GITHUB_WORKSPACE 下寻找模板，无则相对于当前脚本查找
  const rootDir = process.env.GITHUB_WORKSPACE || path.join(__dirname, '../..');
  const templatePath = path.join(rootDir, '.github/template/notify.md');

  if (!fs.existsSync(templatePath)) {
    console.error(`❌ 错误: 找不到钉钉通知模板文件 (${templatePath})`);
    return;
  }

  let content = fs.readFileSync(templatePath, 'utf8');

  // 构建状态友好的显示图标
  const status = process.env.JOB_STATUS === 'success' ? '✅ 成功' : '❌ 失败';

  // 映射环境变量与自定义变量
  const variables = {
    ...process.env,
    JOB_STATUS: status,
    SHORT_SHA: (process.env.GITHUB_SHA || '').substring(0, 7)
  };

  // 支持在 notify.md 中使用任意 ${VAR_NAME} 形式的环境变量
  content = content.replace(/\$\{([A-Z0-9_]+)\}/g, (match, key) => {
    return variables[key] !== undefined ? variables[key] : match;
  });

  let targetUrl = webhook;

  // 钉钉安全加签处理
  if (secret) {
    const timestamp = Date.now();
    const stringToSign = `${timestamp}\n${secret}`;
    const sign = crypto
      .createHmac('sha256', secret)
      .update(stringToSign)
      .digest('base64');
    
    const urlObj = new URL(webhook);
    urlObj.searchParams.append('timestamp', timestamp.toString());
    urlObj.searchParams.append('sign', sign);
    targetUrl = urlObj.toString();
  }

  const payload = JSON.stringify({
    msgtype: 'markdown',
    markdown: {
      title: `${process.env.GITHUB_REPOSITORY || 'GitHub'} 部署通知`,
      text: content
    }
  });

  const url = new URL(targetUrl);
  const options = {
    hostname: url.hostname,
    port: 443,
    path: url.pathname + url.search,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(payload)
    }
  };

  const req = https.request(options, (res) => {
    let data = '';
    res.on('data', (chunk) => data += chunk);
    res.on('end', () => {
      console.log('✅ 钉钉通知发送结果:', data);
    });
  });

  req.on('error', (e) => {
    console.error('❌ 发送钉钉通知异常:', e.message);
  });

  req.write(payload);
  req.end();
}

sendDingTalk();
