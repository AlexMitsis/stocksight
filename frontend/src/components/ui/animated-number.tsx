import { useEffect } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

interface AnimatedNumberProps {
  value: number;
  format: (value: number) => string;
}

export function AnimatedNumber({ value, format }: AnimatedNumberProps) {
  const spring = useSpring(0, { duration: 1000, bounce: 0 });
  const display = useTransform(spring, format);

  useEffect(() => {
    spring.set(value);
  }, [spring, value]);

  return <motion.span>{display}</motion.span>;
}
