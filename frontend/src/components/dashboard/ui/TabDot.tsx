interface TabDotProps {
  color: string;
}

function TabDot({ color }: TabDotProps) {
  return <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: color }} />;
}

export default TabDot;
