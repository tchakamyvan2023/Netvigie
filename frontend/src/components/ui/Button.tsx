import { ButtonHTMLAttributes } from 'react'

export function Button({
  variant = 'default',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'default' | 'primary' | 'danger' }) {
  const cls = variant === 'default' ? 'btn' : `btn ${variant}`
  return <button className={cls} {...props} />
}