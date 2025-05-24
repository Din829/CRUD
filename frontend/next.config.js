/** @type {import('next').NextConfig} */
const nextConfig = {
  // 启用严格模式
  reactStrictMode: true,
  
  // API 重写配置 - 代理到后端
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: 'http://localhost:5003/:path*'
      }
    ]
  },
  
  // 图像优化配置
  images: {
    domains: ['localhost'],
  },
  
  // 实验性功能
  experimental: {
    typedRoutes: false
  }
}

module.exports = nextConfig 