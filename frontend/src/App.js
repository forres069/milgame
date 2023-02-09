import React from "react";
import { App, mainComponents, wrapperComponents } from "logicore-react-pages";

import { useTranslation, Trans } from 'react-i18next';
import './i18n';

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
  return <div><Trans>Hello</Trans>, {props.name}</div>;
};

Object.assign(mainComponents, {
    HomeView,
});

export default App;
