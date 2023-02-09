import React from "react";
import { App, mainComponents, wrapperComponents } from "logicore-react-pages";

const MainWrapper = ({ result, onChange }) => {
  const Component = mainComponents[result?.template];
  return (
    <>
      {Component && result && <Component {...{ ...result, onChange }} />}
    </>
  );
};

Object.assign(wrapperComponents, {
    MainWrapper,
});


const HomeView = (props) => {
  return <div>Hello, {props.name}</div>;
};

Object.assign(mainComponents, {
    HomeView,
});

export default App;
