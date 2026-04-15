import { useEffect } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

interface AnimatedNumberProps {
  value: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
}

export function AnimatedNumber({ value, decimals = 0, prefix = '', suffix = '' }: AnimatedNumberProps) {
  const spring = useSpring(0, { duration: 1000, bounce: 0 });
  const display = useTransform(spring, (current) => {
    const formatted = current.toFixed(decimals);
    const withCommas = formatted.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return `${prefix}${withCommas}${suffix}`;
  });

  useEffect(() => {
    spring.set(value);
  }, [spring, value]);

  return <motion.span>{display}</motion.span>;
}
